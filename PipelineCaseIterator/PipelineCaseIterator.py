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
from PipelineCreator import PipelineCreatorLogic
from PipelineCaseIteratorLibrary import *

# overall - int 0-100 with current overall progress
# currentPipeline - int 0-100 with progress of currently running pipeline
# totalCount - int of total number of files being run over
# currentNumber - index of current file being run over. Zero based
PipelineCaseProgress = collections.namedtuple('PipelineCaseProgress',
                                              "overallPercent currentPipelinePercent totalCount currentNumber")


class PipelineCaseIteratorRunner(object):
    class _ProgressHelper(object):
        def __init__(self, numberOfFiles=0, currentFileIndex=0):
            self.numberOfFiles = numberOfFiles
            self.currentFileIndex = currentFileIndex

    def __init__(self, pipelineName, inputFile, outputDirectory, outputExtension=None, prefix=None, suffix=None,
                 timestampFormat=None, pipelineCreatorLogic=None):

        if not os.path.isfile(inputFile):
            raise RuntimeError("Input directory does not exist or is not a directory: " + inputFile)

        if not os.path.exists(outputDirectory):
            os.makedirs(outputDirectory)

        self._PipelineCreatorLogic = pipelineCreatorLogic or PipelineCreatorLogic()

        self._pipeline = self._PipelineCreatorLogic.registeredPipelines[pipelineName]
        self._inputFile = inputFile
        self._outputDirectory = outputDirectory
        self._progressCallback = None
        self._prefix = prefix
        self._suffix = suffix
        self._timestampFormat = timestampFormat
        self._timestamp = None

        #if outputExtension is None:
        #    with ScopedNode(slicer.mrmlScene.AddNewNodeByClass(self._pipeline.returnType.__vtkname__)) as outputNode:
        #        with ScopedDefaultStorageNode(outputNode) as store:
        #            writeFileTypes = store.GetSupportedWriteFileTypes()
        #            writeFileExts = vtk.vtkStringArray()
        #            store.GetFileExtensionsFromFileTypes(writeFileTypes, writeFileExts)
        #        if writeFileExts.GetNumberOfValues() > 0:
        #            outputExtension = writeFileExts.GetValue(0)
        #        else:
        #            raise Exception('Output extension not specified and unable to deduce a valid extension')
        #elif not outputExtension.startswith('.'):
        #    outputExtension = '.' + outputExtension


        #self._outputExtension = outputExtension
        self._progressHelper = self._ProgressHelper(0, 0)

    def setProgressCallback(self, progressCallback):
        self._progressCallback = progressCallback

    def run(self):
        if self._timestampFormat is not None:
            self._timestamp = datetime.datetime.now().strftime(self._timestampFormat)

        csvParameters = IteratorParameterFile(self._pipeline.parameters, inputFile=self._inputFile)

        # self._pipeline.SetProgressCallback(self._setPipelineProgress)
        rowCount = 0
        outputData = []

        for row in csvParameters:
            try:
                inputParameters, inputNodes = self._rowToTypes(row, self._pipeline.parameters)
                output = self._pipeline.function(**inputParameters)
                outputRow = self._writeNodes(output, rowCount, self._outputDirectory)
                outputData.append(outputRow | row)
            except Exception as e:
                print(f"Exception: {e}")
                traceback.print_exc()
            finally:
                rowCount = rowCount + 1
                for node in inputNodes:
                    slicer.mrmlScene.RemoveNode(node)
            # self._pipeline.SetProgressCallback(None)

        self._writeResults(outputData, self._outputDirectory)

    def _writeResults(self, data: list[dict[str, typing.Any]], outputDirectory: str):
        filename = os.path.join(outputDirectory, "results.csv")
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

    def _setPipelineProgress(self, pipelineProgress):
        currentPipelineProgress = pipelineProgress.progress * 100
        overallProgressBase = self._progressHelper.currentFileIndex / self._progressHelper.numberOfFiles * 100
        if self._progressCallback is not None:
            self._progressCallback(PipelineCaseProgress(
                overallPercent=int(overallProgressBase + currentPipelineProgress / self._progressHelper.numberOfFiles),
                currentPipelinePercent=int(currentPipelineProgress),
                totalCount=self._progressHelper.numberOfFiles,
                currentNumber=self._progressHelper.currentFileIndex,
            ))

    def _rowToTypes(self, csvRow: dict[str, str], inputTypes: dict[str, typing.Any]):
        """
        Converts a row from the csv file to the correct types for the pipeline,
        and loads any nodes that are required.
        Args:
            csvRow (dict[str, str]): The row from the csv file
            inputTypes (dict[str, typing.Any]): The types of the input parameters from the pipelineInfo
        """
        parameters = {}
        nodes = []
        valid = True
        for name, paramType in inputTypes.items():
            if name == "delete_intermediate_nodes":
                continue
            # Verify if
            if issubclass(paramType, slicer.vtkMRMLNode):
                inputNode = slicer.mrmlScene.AddNewNodeByClass(paramType.__name__)
                nodes.append(inputNode)
                with ScopedDefaultStorageNode(inputNode) as store:
                    store.SetFileName(csvRow[name])
                    success = store.ReadData(inputNode)
                    if success == 0:
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
            nodes = None

        return parameters, nodes

    def _writeNodes(self, output, rowCount: int, outputDirectory: str):
        """ Write out all the nodes in a given output, the output is either a single value that
        or a could be a node or a parameterPack that contains nodes
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
            # TODO Should look up parameter name in Output type
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
        self.parent.title = " Pipeline Case Iterator"
        self.parent.categories = ["Pipelines"]
        self.parent.dependencies = ["PipelineCreator"]
        self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
        self.parent.helpText = """
This module allows running a pipeline over multiple files in a directory and output the results in another directory.
"""
        self.parent.acknowledgementText = "This module was originally developed by Connor Bowley (Kitware, Inc.) for SlicerSALT."


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
        self.logic.setProgressCallback(self._progressCallback)
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

    def _progressCallback(self, progress: PipelineCaseProgress):
        self.ui.overallProgressBar.value = progress.overallPercent
        self.ui.overallProgressBar.setFormat(
            '%p% (' + str(progress.currentNumber + 1) + '/' + str(progress.totalCount) + ')')
        self.ui.pipelineProgressBar.value = progress.currentPipelinePercent

    def browseInputFile(self):
        filePicker = qt.QFileDialog(self.parent, "Choose input file", self.ui.inputFileLineEdit.text)
        filePicker.setFileMode(qt.QFileDialog.ExistingFile)

        if filePicker.exec():
            self.ui.inputFileLineEdit.text = filePicker.selectedFiles()[0]

    def createTemplateFile(self):
        filePicker = qt.QFileDialog(self.parent, "Choose input file", self.ui.inputFileLineEdit.text)
        filePicker.setFileMode(qt.QFileDialog.AnyFile)

        if filePicker.exec():
            pipelineInfo = self.PipelineCreatorLogic.registeredPipelines[self.ui.pipelineNameLabel.text]
            parameters = IteratorParameterFile(pipelineInfo.parameters)
            self.ui.inputFileLineEdit.text = filePicker.selectedFiles()[0]
            parameters.createTemplate(self.ui.inputFileLineEdit.text)

    def browseOutputDirectory(self):
        directoryPicker = qt.QFileDialog(self.parent, "Choose input directory", self._browseDirectory)
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
        self.ui.pipelineNameLabel.text = popUp.selectedPipeline.name
        popUp.close()
        popUp.destroy()

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
        self.ui.pipelineProgressBar.value = 0
        inputFile = self.ui.inputFileLineEdit.text
        outputDirectory = self.ui.outputDirectoryLineEdit.text
        pipelineName = self.ui.pipelineNameLabel.text
        outputExtension = self.ui.outputExtensionLineEdit.text if self.ui.outputExtensionLineEdit.text != '' else None
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
                outputExtension=outputExtension,
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

        settings = qt.QSettings()
        settings.setValue('PipelineCaseIterator/LastInputFile', self.ui.inputFileLineEdit.text)
        settings.setValue('PipelineCaseIterator/LastOutputDirectory', self.ui.outputDirectoryLineEdit.text)
        settings.setValue('PipelineCaseIterator/LastPipelineName', self.ui.pipelineNameLabel.text)


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
            outputExtension: str = None,
            prefix: str = None,
            suffix: str = None,
            timestampFormat: str = None):
        # we cheat and know how the PipelineCaseIteratorRunner.py does its job, so we are going
        # to start it to short cut any exceptions and get better error messages
        # but we don't actually run anything in this process
        PipelineCaseIteratorRunner(pipelineInfo.name, inputFile, outputDirectory, outputExtension, prefix, suffix,
                                   timestampFormat)

        script = self.resourcePath('CommandLineScripts/PipelineCaseIteratorRunner.py')
        self._asynchrony = Asynchrony(
            lambda: self._runImpl(
                slicer.app.applicationFilePath(), script,
                pipelineInfo.name, inputFile, outputDirectory,
                outputExtension, prefix, suffix, timestampFormat),
            self._runFinished)
        self._asynchrony.Start()
        self._running = True

    def runSynchronously(self, pipelineInfo: PipelineInfo,
                         inputFile: str,
                         outputDirectory: str,
                         outputExtension: str = None,
                         prefix: str = None,
                         suffix: str = None,
                         timestampFormat: str = None):

        runner = PipelineCaseIteratorRunner(pipelineInfo.name, inputFile, outputDirectory, outputExtension, prefix,
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

    def _runImpl(self, launcherPath, scriptPath, pipelineName, inputFile, outputDirectory, outputExtension, prefix,
                 suffix, timestampFormat):
        positiveIntReStr = '[0-9]+'
        pipelineProgressRe = re.compile(
            '<pipelineProgress>\s*(?P<overall>{integer}),\s*(?P<piece>{integer}),\s*(?P<totalCount>{integer}),\s*(?P<currentNumber>{integer})\s*</pipelineProgress>'.format(
                integer=positiveIntReStr))

        cmd = [
            launcherPath,
            '--python-script',
            scriptPath,
            '--',
            '--pipelineName="%s"' % pipelineName,
            '--inputFile="%s"' % inputFile,
            '--outputDirectory="%s"' % outputDirectory,
        ]
        if outputExtension:  # empty string would do nothing so don't send it
            cmd += ['--outputExtension="%s"' % outputExtension]
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
                        pieceProgress = int(search.group('piece'))
                        totalCount = int(search.group('totalCount'))
                        currentNumber = int(search.group('currentNumber'))
                        Asynchrony.RunOnMainThread(
                            lambda: self._setProgress(overallProgress, pieceProgress, totalCount, currentNumber))
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

    def _setProgress(self, overall, piece, totalCount, currentNumber):
        if self._progressCallback is not None:
            self._progressCallback(PipelineCaseProgress(
                overallPercent=overall,
                currentPipelinePercent=piece,
                totalCount=totalCount,
                currentNumber=currentNumber,
            ))


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
        self.setUp()
        self.test_PipelineCaseIterator1()

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
