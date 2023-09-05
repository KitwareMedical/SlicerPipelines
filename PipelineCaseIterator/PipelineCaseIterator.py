import collections
import datetime
import os
import re
import subprocess
import traceback
import typing
import csv

from slicer.parameterNodeWrapper import (
    isParameterPack,
    splitAnnotations,
    unannotatedType,
)
from Widgets.SelectPipelinePopUp import SelectPipelinePopUp
# SelectModulePopUp
from PipelineCreator import slicerPipeline
from _PipelineCreator.PipelineRegistrar import PipelineInfo
import vtk, qt, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from PipelineCreator import PipelineCreatorLogic, PipelineProgressCallback
from PipelineCaseIteratorLibrary import (
 Asynchrony,
 IteratorParameterFile,
 ScopedNode,
 ScopedDefaultStorageNode
)

# overall - int 0-100 with current overall progress
# currentPipeline - int 0-100 with progress of currently running pipeline
# totalCount - int of total number of files being run over
# currentNumber - index of current file being run over. Zero based
PipelineCaseProgress = collections.namedtuple('PipelineCaseProgress',
                                              "overallPercent currentPipelinePercent totalCount currentNumber")


def rowToTypes(csvRow: dict[str, str], inputTypes: dict[str, typing.Any], baseDirectory : str = "") -> \
        (dict[str, typing.Any], list[slicer.vtkMRMLNode]):
    """Converts a row from the csv file to the correct types for the pipeline,
    and loads any nodes that are required.
    Args:
        csvRow (dict[str, str]): The row from the csv file
        inputTypes (dict[str, typing.Any]): The types of the input parameters from the pipelineInfo
    Returns:
        valid (bool): True iff all files were loaded and of the correct type
        data (dict[str, typing.Any]): The data converted to the ingoing types, None on conversion error
        nodes (list[slicer.vtkMRMLNode]): The nodes that were created, empty list on conversion error
    """
    parameters = {}
    nodes = []
    valid = True

    if baseDirectory == '':
        baseDirectory = os.getcwd()

    for name, paramType in inputTypes.items():
        if name == "delete_intermediate_nodes":
            continue
        # Verify if
        if issubclass(paramType, slicer.vtkMRMLNode):
            inputNode = slicer.mrmlScene.AddNewNodeByClass(paramType.__name__)
            nodes.append(inputNode)
            with ScopedDefaultStorageNode(inputNode) as store:
                # Handle relative filenames
                filePath = csvRow[name]
                if not os.path.isabs(filePath):
                    filePath = os.path.join(baseDirectory, filePath)

                if not os.path.exists(filePath):
                    print(f"Could not load {filePath}, it doesn't exist")
                    valid = False
                    break

                store.SetFileName(filePath)
                success = store.ReadData(inputNode)
                if success == 0:
                    print(f"Could not load {filePath} as {paramType.__name__}")
                    valid = False
                    break
            parameters[name] = inputNode
        else:
            try:
                parameters[name] = paramType(csvRow[name])
            except ValueError:
                print(f"Could not cast {csvRow[name]} to {paramType.__name__}")
                valid = False
                break

    if not valid:
        for node in nodes:
            slicer.mrmlScene.RemoveNode(node)
        parameters = None
        nodes = []

    return valid, parameters, nodes


class PipelineCaseIteratorRunner(object):
    class _ProgressHelper(object):
        def __init__(self, numberOfFiles=0, currentFileIndex=0):
            self.numberOfPasses = numberOfFiles
            self.currentPassIndex = currentFileIndex

    def __init__(self, pipelineName, inputFile, outputDirectory, resultsFileName = "results.csv", prefix=None, suffix=None,
                 timestampFormat=None, pipelineCreatorLogic=None):

        if not os.path.isfile(inputFile):
            raise RuntimeError("Input directory does not exist or is not a directory: " + inputFile)

        # Directory is used to allow relative pathnames in the input file
        self._baseDir = os.path.dirname(os.path.abspath(inputFile))

        if not os.path.exists(outputDirectory):
            os.makedirs(outputDirectory)

        self._PipelineCreatorLogic = pipelineCreatorLogic or PipelineCreatorLogic()

        self._pipeline = self._PipelineCreatorLogic.registeredPipelines[pipelineName]
        self._inputFile = inputFile
        self._outputDirectory = outputDirectory
        self._resultsFileName = resultsFileName if resultsFileName.endswith('.csv') else resultsFileName + '.csv'

        # Note this is the inner callback to a PipelineProgressCallback object i.e
        # progress == PipelineProgressCallback(self._progressCallback)
        self._progressCallbackFunction = None
        self._prefix = prefix
        self._suffix = suffix
        self._timestampFormat = timestampFormat
        self._timestamp = None
        self._progressHelper = self._ProgressHelper(0, 0)

    def setProgressCallback(self, progressCallback):
        self._progressCallbackFunction = progressCallback

    def run(self):
        if self._timestampFormat is not None:
            self._timestamp = datetime.datetime.now().strftime(self._timestampFormat)

        csvParameters = IteratorParameterFile(self._pipeline.parameters, inputFile=self._inputFile)

        callback = PipelineProgressCallback()
        callback.setCallback(self._setPipelineProgress)
        self._progressHelper.numberOfPasses = len(csvParameters)

        outputData = []
        inputNodes = []

        for passIndex, row in enumerate(csvParameters):
            try:
                self._progressHelper.currentPassIndex = passIndex
                valid, inputParameters, inputNodes = rowToTypes(row, self._pipeline.parameters, baseDirectory=self._baseDir)
                if valid:
                    output = self._pipeline.function(**inputParameters, progress_callback=callback)
                    outputRow = self._postProcessPipelineOutput(output, passIndex, self._outputDirectory)
                    outputData.append(outputRow | row)
                else:
                    print(f"Invalid data in row {passIndex}, skipping ...")
            except Exception as e:
                print(f"Exception: {e}")
                traceback.print_exc()
            finally:
                for node in inputNodes:
                    slicer.mrmlScene.RemoveNode(node)

        self._writeResults(outputData, self._outputDirectory)

    def _writeResults(self, data: list[dict[str, typing.Any]], outputDirectory: str):
        filename = os.path.join(outputDirectory, self._resultsFileName)
        if not data:
            return
        fieldnames = data[0].keys()
        with open(filename, mode='w+', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)

    def _createOutputFilepath(self, baseFilename, outputExtension, outputDirectory):
        # Get filename and strip extension
        outputFilename = os.path.splitext(os.path.basename(baseFilename))[0]
        if self._prefix is not None:
            outputFilename = self._prefix + outputFilename
        if self._suffix is not None:
            outputFilename = outputFilename + self._suffix
        if self._timestamp is not None:
            outputFilename = outputFilename + self._timestamp
        outputFilename += outputExtension
        return os.path.normpath(os.path.join(outputDirectory, outputFilename))

    def _setPipelineProgress(self,
                             totalSubProgress,
                             currentPipelinePieceName,
                             currentPipelineSubPieceNumber,
                             numberOfSubPieces):
        """Converts the progress of one pipeline into overall progress of the Case Iterator"""
        currentPipelineProgress = totalSubProgress + currentPipelineSubPieceNumber / numberOfSubPieces
        overallProgressBase = self._progressHelper.currentPassIndex / self._progressHelper.numberOfPasses
        if self._progressCallbackFunction is not None:
            totalProgress = overallProgressBase + currentPipelineProgress / self._progressHelper.numberOfPasses
            self._progressCallbackFunction(
                totalProgress,
                currentPipelinePieceName,
                self._progressHelper.currentPassIndex,
                self._progressHelper.numberOfPasses,
            )

    def _postProcessPipelineOutput(self, output, rowCount: int, outputDirectory: str) -> dict[str, str]:
        """ Processes the output of a pipeline the output can either be a ParameterPack or
        a single value. For each node in the output, write that node to a file. Returns a
        dictionary with all the outputs file names if they are nodes, or their value otherwise
        """
        nodes = {}
        outputRow = {}

        if isParameterPack(output):
            for param in output.allParameters:
                value = output.getValue(param)
                if issubclass(value.__class__, slicer.vtkMRMLNode):
                    nodes[param] = value
                else:
                    outputRow[param] = output.getValue(param)
        elif issubclass(output.__class__, slicer.vtkMRMLNode):
            nodes["returnValue"] = output

        # Iterates over all nodes in the output, stores them to file
        # additionally releases them after writing through the ScopedNode
        for name, outputNode in nodes.items():
            with ScopedNode(outputNode) as node:
                with ScopedDefaultStorageNode(node) as storageNode:
                    fileTypes = storageNode.GetSupportedWriteFileTypes()
                    fileExtensions = vtk.vtkStringArray()
                    storageNode.GetFileExtensionsFromFileTypes(fileTypes, fileExtensions)
                    outputExtension = fileExtensions.GetValue(0)
                    # TODO Figure out basename from pipeline
                    outputFilepath = self._createOutputFilepath(f'{name}_{rowCount:03d}',
                                                                outputExtension,
                                                                outputDirectory, )
                    if slicer.util.saveNode(node, outputFilepath):
                        outputRow[name] = outputFilepath
                    else:
                        print(f'Failed to write node {node} to disk at {outputFilepath} \n'
                              + 'Try checking the error log for more details')
        return outputRow
#
# PipelineCaseIterator
#


class PipelineCaseIterator(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Pipeline Case Iterator"
        self.parent.categories = ["Pipelines"]
        self.parent.dependencies = ["PipelineCreator"]
        self.parent.contributors = ["Connor Bowley (Kitware, Inc.)", "Harald Scheirich (Kitware, Inc.)", "David Allemang (Kitware, Inc.)"]
        self.parent.helpText = """
<p>The case iterator lets you repeat the same pipeline operation over a any amount of data. To operate it follow the following steps:</p>
<ol>
<li>Select a pipeline that you want to execute</li>
<li>Write a template input file. This will create a `.csv` file that has a column for each input parameter for the given pipeline. Each row in the input file will trigger one iteration of the pipeline with the given data. For each row every column has to be filled out. If the input data is a node, the entry should be a path to the data for that node</li>
<li>Select a directory for the output. The output will consist in another `.csv` file that contains all the input and output data for that run, whenever a node is in the resulting data of a run the appropriate path will be in the output .csv file.</li>
<li>Optionally choose whether you want to prepend, append fixed strings to the output data or add a timestamp. The timestamp will be the time of the beginning of the run, this means that all output date from one run will have the same timestamp.</li>
<li>Press "Run", this will start executing the pipeline with the given data. When you press run a second copy of slicer will be started to do the actual calculation. if all or part of a given data for a pass it will be skipped and a message will show in the console. The progress of the run can be seen in the progress bar. You can always abort a run using the "Cancel" button.</li>
</ol>
<p>Note: When creating a template `.csv` file, each column name will show the name for the given parameter and its type</p>
"""
        self.parent.acknowledgementText = "This module was originally developed by Connor Bowley (Kitware, Inc.) for SlicerSALT (R01EB021391)."


#
# PipelineCaseIteratorWidget
#

class PipelineCaseIteratorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def __init__(self, parent=None):
        """
    Called when the user opens the module the first time and the widget is initialized.
    """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._browseDirectory = os.path.expanduser("~")
        self.PipelineCreatorLogic = PipelineCreatorLogic()

    def setup(self):
        """
    Called when the user opens the module the first time and the widget is initialized.
    """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/PipelineCaseIterator.ui'))
        self.layout.addWidget(self.uiWidget)
        self.ui = slicer.util.childWidgetVariables(self.uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        self.uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = PipelineCaseIteratorLogic()
        self.logic.setProgressCallback(self._updateProgressBars)
        self.logic.setFinishedCallback(self._runFinished)

        # Connections

        self.ui.inputFileBrowseButton.clicked.connect(self.browseInputFile)
        self.ui.createTemplateFileButton.clicked.connect(self.createTemplateFile)
        self.ui.outputDirectoryBrowseButton.clicked.connect(self.browseOutputDirectory)
        self.ui.pipelineSelectionButton.clicked.connect(self.selectPipeline)
        self.ui.runButton.clicked.connect(self.run)
        self.ui.cancelButton.clicked.connect(self.cancel)

        # Default Values

        settings = qt.QSettings()
        self.ui.inputFileLineEdit.text = settings.value('PipelineCaseIterator/LastInputFile')
        self.ui.outputDirectoryLineEdit.text = settings.value('PipelineCaseIterator/LastOutputDirectory',
                                                              os.path.expanduser("~"))
        self._browseDirectory = self.ui.outputDirectoryLineEdit.text
        self.ui.pipelineNameLabel.text = settings.value('PipelineCaseIterator/LastPipelineName', '')
        self.ui.resultsFileNameLineEdit.text = settings.value('PipelineCaseIterator/LastResultFileName', 'results')

        self._validateInputs(doWarn=False)

    def _updateProgressBars(self, overallPercent, pipelineName, currentNumber, totalCount):
        self.ui.overallProgressBar.value = overallPercent
        self.ui.overallProgressBar.setFormat(
            '%p% (' + str(currentNumber + 1) + '/' + str(totalCount) + ')')

    def browseInputFile(self):
        filePicker = qt.QFileDialog(self.parent, "Choose input file", self.ui.inputFileLineEdit.text)
        filePicker.setFileMode(qt.QFileDialog.ExistingFile)

        if filePicker.exec():
            self.ui.inputFileLineEdit.text = filePicker.selectedFiles()[0]
            self._validateInputs()

    def createTemplateFile(self):
        filePicker = qt.QFileDialog(self.parent, "Template file", self.ui.inputFileLineEdit.text)
        filePicker.setFileMode(qt.QFileDialog.AnyFile)

        if filePicker.exec():
            pipelineInfo = self.PipelineCreatorLogic.registeredPipelines[self.ui.pipelineNameLabel.text]
            parameters = IteratorParameterFile(pipelineInfo.parameters)
            self.ui.inputFileLineEdit.text = filePicker.selectedFiles()[0]
            parameters.createTemplate(self.ui.inputFileLineEdit.text)
            self._validateInputs()

    def browseOutputDirectory(self):
        directoryPicker = qt.QFileDialog(self.parent, "Choose output directory", self._browseDirectory)
        directoryPicker.setFileMode(qt.QFileDialog.Directory)
        directoryPicker.setOption(qt.QFileDialog.ShowDirsOnly, True)

        if directoryPicker.exec():
            self.ui.outputDirectoryLineEdit.text = directoryPicker.selectedFiles()[0]
            self._browseDirectory = directoryPicker.selectedFiles()[0]

    def selectPipeline(self):
        popUp = SelectPipelinePopUp(self.PipelineCreatorLogic.registeredPipelines, parent=self.uiWidget)
        popUp.accepted.connect(lambda: self._onPopUpAccepted(popUp))
        popUp.open()
        pass

    def _onPopUpAccepted(self, popUp: SelectPipelinePopUp):
        oldPipe = self.ui.pipelineNameLabel.text
        newPipe = popUp.selectedPipeline.name
        popUp.close()
        popUp.destroy()
        if oldPipe != newPipe:
            self.ui.pipelineNameLabel.text = newPipe
            self._validateInputs(False)

    def _validateInputs(self, doWarn = True) -> bool:
        if self.ui.pipelineNameLabel.text == "" or self.ui.inputFileLineEdit.text == "":
            self.ui.runButton.enabled = False
            return False

        pipelineName = self.ui.pipelineNameLabel.text
        inputFilename = self.ui.inputFileLineEdit.text

        pipelines = PipelineCreatorLogic().registeredPipelines
        pipeline = pipelines[pipelineName]
        file = IteratorParameterFile(pipeline.parameters)
        isValid = file.validate(inputFilename)

        if not isValid:
            self.ui.inputFileLineEdit.text = ""
            if doWarn:
                msgbox = qt.QMessageBox()
                msgbox.setWindowTitle('Error in parameter file')
                msgbox.setText('The given file cannot be run with the pipeline that you chose ' +
                            'not all of the parameters of the pipeline are satisfied, please ' +
                            'chose another file or edit the one you selected.')
                msgbox.exec()

        self.ui.runButton.enabled = isValid

        return isValid

    def cancel(self):
        self.logic.cancel()

    def _runFinished(self, exception):
        self.ui.runButton.enabled = True
        self.ui.cancelButton.enabled = False

        if exception is not None:
            msgbox = qt.QMessageBox()
            msgbox.setWindowTitle('Error running pipeline case iterator')
            if not isinstance(exception, CaseIteratorSubProcessError):
                # don't show the traceback if the subprocess returned a non-zero error because
                # it is not useful
                msgbox.setText(
                    str(exception) + '\n\n' + "".join(traceback.TracebackException.from_exception(exception).format()))
            else:
                msgbox.setText(str(exception))
            msgbox.exec()

    def run(self):
        self.ui.overallProgressBar.value = 0
        self.ui.overallProgressBar.setFormat('%p% (0/0)')
        inputFile = self.ui.inputFileLineEdit.text
        outputDirectory = self.ui.outputDirectoryLineEdit.text
        pipelineName = self.ui.pipelineNameLabel.text
        resultsFileName = self.ui.resultsFileNameLineEdit.text
        if resultsFileName == '':
            resultsFileName = 'results.csv'

        prefix = self.ui.outputPrefixLineEdit.text  # empty string is acceptable
        suffix = self.ui.outputSuffixLineEdit.text  # empty string is acceptable
        timestampFormat = self.ui.timestampFormatLineEdit.text if self.ui.addTimestampCheckbox.checked else None

        errors = []
        if outputDirectory == "":
            errors += ["The output directory must be specified"]
        if pipelineName == "":
            errors += ["A pipeline must be chosen"]
        if errors:
            msgbox = qt.QMessageBox()
            msgbox.setWindowTitle('Error starting pipeline case iterator')
            msgbox.setText('\n'.join(errors))
            msgbox.exec()
            return

        try:
            pipelineInfo = self.PipelineCreatorLogic.registeredPipelines[pipelineName]
            self.logic.run(
                pipelineInfo=pipelineInfo,
                inputFile=inputFile,
                outputDirectory=outputDirectory,
                resultsFileName=resultsFileName,
                prefix=prefix,
                suffix=suffix,
                timestampFormat=timestampFormat)
            self.ui.runButton.enabled = False
            self.ui.cancelButton.enabled = True
        except Exception as e:
            msgbox = qt.QMessageBox()
            msgbox.setWindowTitle('Error starting pipeline case iterator')
            msgbox.setText(str(e) + '\n\n' + "".join(traceback.TracebackException.from_exception(e).format()))
            msgbox.exec()

    def cleanup(self):
        """
    Called when the application closes and the module widget is destroyed.
    """
        self.removeObservers()

        self._safeSetValue('PipelineCaseIterator/LastInputFile', self.ui.inputFileLineEdit)
        self._safeSetValue('PipelineCaseIterator/LastOutputDirectory', self.ui.outputDirectoryLineEdit)
        self._safeSetValue('PipelineCaseIterator/LastPipelineName', self.ui.pipelineNameLabel)
        self._safeSetValue('PipelineCaseIterator/LastResultsFileName', self.ui.resultsFileNameLineEdit)

    def _safeSetValue(self, settingsLabel, widget):
        if not widget:
            return

        settings = qt.QSettings()
        settings.setValue(settingsLabel, widget.text)

class CaseIteratorSubProcessError(Exception):
    pass


#
# PipelineCaseIteratorLogic
#

class PipelineCaseIteratorLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    class _ProgressHelper(object):
        def __init__(self, numberOfFiles=0, currentFileIndex=0):
            self.numberOfFiles = numberOfFiles
            self.currentFileIndex = currentFileIndex

    def resourcePath(self, filename):
        scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
        return os.path.join(scriptedModulesPath, 'Resources', filename)

    def __init__(self):
        """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
        ScriptedLoadableModuleLogic.__init__(self)

        self._progressCallback = None
        self._asynchrony = None
        self._running = False
        self._finishCallback = None

    def setProgressCallback(self, progressCallback=None):
        self._progressCallback = progressCallback

    def cancel(self):
        if self._asynchrony is not None:
            self._asynchrony.Cancel()

    def setFinishedCallback(self, finishCallback=None):
        self._finishCallback = finishCallback

    def run(self, pipelineInfo: PipelineInfo,
            inputFile: str,
            outputDirectory: str,
            resultsFileName: str = 'results.csv',
            prefix: str = None,
            suffix: str = None,
            timestampFormat: str = None):
        # we cheat and know how the PipelineCaseIteratorRunner.py does its job, so we are going
        # to start it to short cut any exceptions and get better error messages
        # but we don't actually run anything in this process
        PipelineCaseIteratorRunner(pipelineInfo.name, inputFile, outputDirectory, resultsFileName, prefix, suffix,
                                   timestampFormat)

        script = self.resourcePath('CommandLineScripts/PipelineCaseIteratorRunner.py')
        self._asynchrony = Asynchrony(
            lambda: self._runImpl(
                slicer.app.applicationFilePath(), script,
                pipelineInfo.name, inputFile, outputDirectory, resultsFileName,
                prefix, suffix, timestampFormat),
            self._runFinished)
        self._asynchrony.Start()
        self._running = True

    def runSynchronously(self, pipelineInfo: PipelineInfo,
                         inputFile: str,
                         outputDirectory: str,
                         resultsFileName: str = None,
                         prefix: str = None,
                         suffix: str = None,
                         timestampFormat: str = None):
        """Executes the pipeline synchronously inside of slicer, allows for better testing
        """

        runner = PipelineCaseIteratorRunner(pipelineInfo.name, inputFile, outputDirectory, resultsFileName, prefix,
                                            suffix, timestampFormat)
        runner.run()

    @property
    def running(self):
        return self._running

    def _runFinished(self):
        self._running = False
        try:
            self._asynchrony.GetOutput()
            if self._finishCallback is not None:
                self._finishCallback(None)
        except Asynchrony.CancelledException:
            # if they cancelled, the finish was as expected
            if self._finishCallback is not None:
                self._finishCallback(None)
        except Exception as e:
            if self._finishCallback is not None:
                self._finishCallback(e)
        finally:
            self._asynchrony = None

    def _runImpl(self, launcherPath, scriptPath, pipelineName, inputFile, outputDirectory, resultsFileName,
                 prefix, suffix, timestampFormat):
        positiveIntReStr = '[0-9]+'
        # TODO check the name regex against the pipeline naming conventions
        pipelineProgressRe = re.compile(
            '<pipelineProgress>\s*(?P<overall>{integer}),\s*(?P<pipelineName>[a-zA-Z0-9_.]*),\s*(?P<currentNumber>{integer}),\s*(?P<totalCount>{integer})\s*</pipelineProgress>'.format(
                integer=positiveIntReStr))

        cmd = [
            launcherPath,
            '--python-script',
            scriptPath,
            '--',
            '--pipelineName="%s"' % pipelineName,
            '--inputFile="%s"' % inputFile,
            '--outputDirectory="%s"' % outputDirectory,
            '--resultsFileName="%s"' % resultsFileName,
        ]
        if prefix:  # empty string would do nothing so don't send it
            cmd += ['--prefix="%s"' % prefix]
        if suffix:  # empty string would do nothing so don't send it
            cmd += ['--suffix="%s"' % suffix]
        if timestampFormat:  # empty string would do nothing so don't send it
            cmd += ['--timestampFormat="%s"' % timestampFormat]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        totalCount = 0

        try:
            while True:
                Asynchrony.CheckCancelled()
                output = proc.stdout.readline()
                if not output and proc.poll() is not None:
                    break
                if output:
                    textOutput = output.decode('ascii')
                    search = re.search(pipelineProgressRe, textOutput)
                    if search:
                        overallProgress = int(search.group('overall'))
                        pipelineName = search.group('pipelineName')
                        totalCount = int(search.group('totalCount'))
                        currentNumber = int(search.group('currentNumber'))
                        Asynchrony.RunOnMainThread(
                            lambda: self._setProgress(overallProgress, pipelineName, currentNumber, totalCount))
                    print(
                        textOutput.strip())  # prints the output as if it were run in this process. Useful for debugging.
            if proc.poll() == 0:
                Asynchrony.RunOnMainThread(lambda: self._setProgress(100, 100, totalCount, totalCount - 1))
            else:
                raise CaseIteratorSubProcessError('Error running pipeline case iterator runner')
        except:
            proc.terminate()
            raise
        finally:
            proc.stdout.close()

    def _setProgress(self, overall, pipelineName : str, totalCount, currentNumber):
        if self._progressCallback is not None:
            self._progressCallback(
                overall,
                pipelineName,
                totalCount,
                currentNumber,
            )


#
# PipelineCaseIteratorTest
#

class PipelineCaseIteratorTest(ScriptedLoadableModuleTest):
    """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
    """
        import unittest
        from Testing.Python.IteratorParametersTest import IteratorParametersTest
        from Testing.Python.CaseIteratorRunnerTest import RowToTypesTest
        loader = unittest.defaultTestLoader
        suite = unittest.TestSuite()
        suite.addTest(loader.loadTestsFromTestCase(IteratorParametersTest))
        suite.addTest(loader.loadTestsFromTestCase(RowToTypesTest))
        unittest.TextTestRunner().run(suite)

    def test_PipelineCaseIterator1(self):
        """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """
        self.delayDisplay("Running unimplemented test")
