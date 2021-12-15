import collections
import os
import traceback

from Widgets.SelectModulePopUp import SelectModulePopUp
import vtk, qt, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from PipelineCreator import PipelineCreatorLogic
from PipelineCreatorLib.PipelineBases import PipelineInterface
from PipelineModulesLib.Util import ScopedNode, ScopedDefaultStorageNode

# overall - int 0-100 with current overall progress
# currentPipeline - int 0-100 with progress of currently running pipeline
# totalCount - int of total number of files being run over
# currentNumber - index of current file being run over. Zero based
PipelineCaseProgress = collections.namedtuple('PipelineCaseProgress',
  "overallPercent currentPipelinePercent totalCount currentNumber")

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
    self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
    self.parent.helpText = """
This module allows running a pipeline over multiple files in a directory and output the results in another directory.
"""
    self.parent.acknowledgementText = ""

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
    self.pipelineCreatorLogic = PipelineCreatorLogic()

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

    # Connections

    self.ui.inputDirectoryBrowseButton.clicked.connect(self.browseInputDirectory)
    self.ui.outputDirectoryBrowseButton.clicked.connect(self.browseOutputDirectory)
    self.ui.pipelineSelectionButton.clicked.connect(self.selectPipeline)
    self.ui.runButton.clicked.connect(self.run)

  def _progressCallback(self, progress):
    self.ui.overallProgressBar.value = progress.overallPercent
    self.ui.overallProgressBar.setFormat('%p% ('+str(progress.currentNumber+1) + '/' + str(progress.totalCount) + ')')
    self.ui.pipelineProgressBar.value = progress.currentPipelinePercent

  def browseInputDirectory(self):
    directoryPicker = qt.QFileDialog(self.parent, "Choose input directory", self._browseDirectory)
    directoryPicker.setFileMode(qt.QFileDialog.Directory)
    directoryPicker.setOption(qt.QFileDialog.ShowDirsOnly, True)

    if directoryPicker.exec():
      self.ui.inputDirectoryLineEdit.text = directoryPicker.selectedFiles()[0]
      self._browseDirectory = directoryPicker.selectedFiles()[0]

  def browseOutputDirectory(self):
    directoryPicker = qt.QFileDialog(self.parent, "Choose input directory", self._browseDirectory)
    directoryPicker.setFileMode(qt.QFileDialog.Directory)
    directoryPicker.setOption(qt.QFileDialog.ShowDirsOnly, True)

    if directoryPicker.exec():
      self.ui.outputDirectoryLineEdit.text = directoryPicker.selectedFiles()[0]
      self._browseDirectory = directoryPicker.selectedFiles()[0]

  def selectPipeline(self):
    popUp = SelectModulePopUp(self.pipelineCreatorLogic.allModules, parent=self.uiWidget)
    popUp.accepted.connect(lambda: self._onPopUpAccepted(popUp))
    popUp.open()

  def _onPopUpAccepted(self, popUp):
    self.ui.pipelineNameLabel.text = popUp.chosenModule.GetName()
    popUp.close()
    popUp.destroy()

  def run(self):
    self.ui.overallProgressBar.value = 0
    self.ui.pipelineProgressBar.value = 0
    inputDirectory = self.ui.inputDirectoryLineEdit.text
    outputDirectory = self.ui.outputDirectoryLineEdit.text
    pipelineName = self.ui.pipelineNameLabel.text
    outputExtension = self.ui.outputExtensionLineEdit.text if self.ui.outputExtensionLineEdit.text != '' else None
    prefix = self.ui.outputPrefixLineEdit.text # empty string is acceptable
    suffix = self.ui.outputSuffixLineEdit.text # empty string is acceptable

    try:
      errors = []
      if inputDirectory == "":
        errors += ["The input directory must be specified"]
      if outputDirectory == "":
        errors += ["The output directory must be specified"]
      if pipelineName == "":
        errors += ["A pipeline must be chosen"]
      if errors:
        raise Exception('\n'.join(errors))

      pipelineInterface = self.pipelineCreatorLogic.moduleFromName(pipelineName)
      self.logic.run(
        pipelineInterface=pipelineInterface,
        inputDirectory=inputDirectory,
        outputDirectory=outputDirectory,
        outputExtension=outputExtension,
        prefix=prefix,
        suffix=suffix)

    except Exception as e:
      msgbox = qt.QMessageBox()
      msgbox.setWindowTitle('Error running pipeline case iterator')
      msgbox.setText(str(e) + '\n\n' + "".join(traceback.TracebackException.from_exception(e).format()))
      msgbox.exec()


  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

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

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    self._progressCallback = None
    self._progressHelper = PipelineCaseIteratorLogic._ProgressHelper(0,0)

  def setProgressCallback(self, progressCallback=None):
    self._progressCallback = progressCallback

  def run(self, pipelineInterface, inputDirectory, outputDirectory, outputExtension = None, prefix=None, suffix=None):
    if not issubclass(pipelineInterface, PipelineInterface):
      raise TypeError("pipeline interface must be a PipelineBases.PipelineInterface")

    if not os.path.isdir(inputDirectory):
      raise RuntimeError("Input directory does not exist or is not a directory: " + inputDirectory)

    if not os.path.exists(outputDirectory):
      os.makedirs(outputDirectory)

    pipeline = pipelineInterface()
    pipeline.SetProgressCallback(self._setPipelineProgress)

    if outputExtension is None:
      with ScopedNode(slicer.mrmlScene.AddNewNodeByClass(pipeline.GetOutputType())) as outputNode:
        with ScopedDefaultStorageNode(outputNode) as store:
          store = outputNode.CreateDefaultStorageNode()
          writeFileTypes = store.GetSupportedWriteFileTypes()
          writeFileExts = vtk.vtkStringArray()
          store.GetFileExtensionsFromFileTypes(writeFileTypes, writeFileExts)
        if writeFileExts.GetNumberOfValues() > 0:
          outputExtension = writeFileExts.GetValue(0)
        else:
          raise Exception('Output extension not specified and unable to deduce a valid extension')
    elif not outputExtension.startswith('.'):
      outputExtension = '.' + outputExtension

    filenames = os.listdir(inputDirectory)
    self._progressHelper.numberOfFiles = len(filenames)
    for index, filename in enumerate(filenames):
      self._progressHelper.currentFileIndex = index
      inputFilepath = os.path.join(inputDirectory, filename)
      outputFilepath = self._createOutputFilepath(filename, outputDirectory, outputExtension, prefix, suffix)
      self._runOnFile(pipeline, inputFilepath, outputFilepath)

    if self._progressCallback is not None:
      self._progressCallback(PipelineCaseProgress(
        overallPercent=100,
        currentPipelinePercent=100,
        totalCount=self._progressHelper.numberOfFiles,
        currentNumber=self._progressHelper.currentFileIndex,
      ))

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

  # inputFilename should be just the file name, no path
  def _createOutputFilepath(self, inputFilename, outputDirectory, outputExtension, prefix=None, suffix=None):
    outputFilename = os.path.splitext(inputFilename)[0]
    if prefix is not None:
      outputFilename = prefix + outputFilename
    if suffix is not None:
      outputFilename = outputFilename + suffix
    outputFilename += outputExtension
    return os.path.join(outputDirectory, outputFilename)

  def _loadInputNode(self, pipeline, inputFilename):
    inputNode = slicer.mrmlScene.AddNewNodeByClass(pipeline.GetInputType())
    with ScopedDefaultStorageNode(inputNode) as store:
      store.SetFileName(inputFilename)
      store.ReadData(inputNode)
    return inputNode

  def _runOnFile(self, pipeline, inputFilename, outputFilename):
    with ScopedNode(self._loadInputNode(pipeline, inputFilename)) as inputNode:
      with ScopedNode(pipeline.Run(inputNode)) as outputNode:
        success = slicer.util.saveNode(outputNode, outputFilename)
        if not success:
          raise Exception('Failed to save node to file: ' + outputFilename + '\nTry checking the error log for more details')


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
