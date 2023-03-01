import copy
import keyword
import os
import pickle
import shutil
import textwrap
import threading
import traceback

import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

from Widgets.PipelineModuleListWidget import PipelineModuleListWidget
from LegacyPipelineCreatorLib._Private.ModuleTemplate import ModuleTemplate
from LegacyPipelineCreatorLib.PipelineBases import PipelineInterface, ProgressablePipeline # ProgressablePipeline import needed for test run to work

def CloneInto(src, dest):
  '''
  Clones src into dest, but keeps dest's display and storage nodes, if any
  If neither src nor dest has display nodes, the default are created
  '''
  if src is not None and dest is not None:
    name = dest.GetName()
    if dest.IsA('vtkMRMLDisplayableNode'):
      displayNodesIDs = [dest.GetNthDisplayNodeID(n) for n in range(dest.GetNumberOfDisplayNodes())]
      storageNodesIDs = [dest.GetNthStorageNodeID(n) for n in range(dest.GetNumberOfStorageNodes())]

    dest.Copy(src)
    dest.SetName(name)

    if dest.IsA('vtkMRMLDisplayableNode'):
      dest.RemoveAllDisplayNodeIDs()
      for n, displayNodeID in enumerate(displayNodesIDs):
        dest.SetAndObserveNthDisplayNodeID(n, displayNodeID)
      for n, storageNodeID in enumerate(storageNodesIDs):
        dest.SetAndObserveNthStorageNodeID(n, storageNodeID)

#
# LegacyPipelineCreator
#

class LegacyPipelineCreator(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Legacy Pipeline Creator"
    self.parent.categories = ["Pipelines"]
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
    self.parent.helpText = """
This is module offers the ability to create simple modules (aka pipelines) via a GUI interface with no coding knowledge needed
See more information in <a href="https://github.com/KitwareMedical/SlicerPipelines/blob/main/README.md">module documentation</a>.
"""
    self.parent.acknowledgementText = "This module was originally developed by Connor Bowley (Kitware, Inc.) for SlicerSALT."

  def createLogic(self):
    return LegacyPipelineCreatorLogic()

#
# LegacyPipelineCreatorWidget
#

class LegacyPipelineCreatorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
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
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False
    self._runPipelineProgressDialog = None

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/LegacyPipelineCreator.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)
    self.uiLayout = self.uiWidget.layout()

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    self.uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = LegacyPipelineCreatorLogic()
    self.logic.setPipelineProgressCallback(self._runPipelineProgress)

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    self.ui.cboxTestInput.setMRMLScene(slicer.mrmlScene)
    self.ui.cboxTestOutput.setMRMLScene(slicer.mrmlScene)
    self.ui.cboxTestInput.enabled = False
    self.ui.cboxTestOutput.enabled = False

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.leModuleName.textChanged.connect(self.updateParameterNodeFromGUI)

    self.ui.btnFinalize.clicked.connect(self._onFinalize)
    self.ui.btnClear.clicked.connect(self._onClear)
    self.ui.btnBrowseOutputDirectory.clicked.connect(self._onBrowseOutputDirectory)
    self.ui.btnRun.clicked.connect(self._onRun)

    self._moduleListWidget = PipelineModuleListWidget()
    self._moduleListWidget.setAvailableModules(self.logic.allModules)
    self._moduleListWidget.modified.connect(self._modulesChanged)
    # insert at count-1 because we want to keep the spacer on the bottom
    self.uiLayout.insertWidget(self.uiLayout.count() - 1, self._moduleListWidget)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

  def _onBrowseOutputDirectory(self):
    directoryPicker = qt.QFileDialog(self.parent, "Choose directory to save module to", os.path.expanduser("~"))
    directoryPicker.setFileMode(qt.QFileDialog.Directory)
    directoryPicker.setOption(qt.QFileDialog.ShowDirsOnly, True)

    if directoryPicker.exec():
      self.ui.leOutputDirectory.text = directoryPicker.selectedFiles()[0]

  def _onClear(self):
    q = qt.QMessageBox()
    q.setWindowTitle("Clearing pipeline")
    q.setText("Are you sure you to start over on the pipeline? This cannot be undone.")
    q.addButton(qt.QMessageBox.Yes)
    q.addButton(qt.QMessageBox.No)

    if q.exec() == qt.QMessageBox.Yes:
      self.ui.leModuleName.text = ""
      self.ui.leOutputDirectory.text = ""
      self.ui.leInputType.text = ""
      self.ui.leOutputType.text = ""
      self._moduleListWidget.clear()

  def _convertModuleListWidgetToLogicInput(self):
    return [
      (name, {
        paramTup[0]: paramTup[-1].GetValue() for paramTup in parameters #TODO if param is fixed
      }) for name, parameters in self._moduleListWidget.getAllParameters()
    ]

  def _onFinalize(self):
    try:
      modules = self._convertModuleListWidgetToLogicInput()
      moduleName = self.ui.leModuleName.text
      outputDirectory = self.ui.leOutputDirectory.text
      self.logic.createPipeline(moduleName, outputDirectory, modules)

      msgbox = qt.QMessageBox()
      msgbox.setWindowTitle("SUCCESS")
      msgbox.setText("Successfully created Pipeline '%s' at '%s'!" % (moduleName, outputDirectory))

      try:
        # add to currently loaded modules
        if self.ui.chkboxLoadModuleOnCreation.isChecked():
          factory = slicer.app.moduleManager().factoryManager()
          factory.registerModule(qt.QFileInfo(os.path.join(outputDirectory, moduleName + ".py")))
          factory.loadModules([moduleName])

        # add to additional search paths
        if self.ui.chkboxAddToAdditionalModulePaths.isChecked():
          settings = slicer.app.revisionUserSettings()

          rawSearchPaths = settings.value("Modules/AdditionalPaths") or []
          if isinstance(rawSearchPaths, str):
            rawSearchPaths = [rawSearchPaths]
          if not isinstance(rawSearchPaths, list):
            # if it returns a tuple or other iterable, make it a list
            rawSearchPaths = list(rawSearchPaths)

          if outputDirectory not in [qt.QDir(rawPath) for rawPath in rawSearchPaths]:
            rawSearchPaths.append(outputDirectory)
            settings.setValue("Modules/AdditionalPaths", rawSearchPaths)
      except Exception as e:
        msgbox.setWindowTitle("Partial Success")
        msgbox.setText(msgbox.text + "\n Post creation failure: " + str(e))

      msgbox.exec()
    except Exception as e:
      msgbox = qt.QMessageBox()
      msgbox.setWindowTitle("Error creating pipeline")
      msgbox.setText(str(e))
      msgbox.exec()

  def _onRun(self):
    try:
      modules = self._convertModuleListWidgetToLogicInput()
      inputNode = self.ui.cboxTestInput.currentNode()
      desiredOutputNode = self.ui.cboxTestOutput.currentNode()
      if desiredOutputNode is None:
        raise Exception("An output node must be chosen")
      if desiredOutputNode.IsA('vtkMRMLDisplayableNode'):
        desiredOutputNode.CreateDefaultDisplayNodes()

      self._runPipelineProgressDialog = slicer.util.createProgressDialog()
      self._runPipelineProgressDialog.setCancelButton(None)
      self._runPipelineProgressDialog.setWindowFlags(qt.Qt.Window | qt.Qt.WindowTitleHint | qt.Qt.CustomizeWindowHint)
      actualOutputNode = self.logic.runPipeline(modules, inputNode)
      CloneInto(actualOutputNode, desiredOutputNode)

      if inputNode.IsA('vtkMRMLDisplayableNode') and inputNode.GetDisplayNode() is not None:
        inputNode.GetDisplayNode().SetVisibility(False)
      if desiredOutputNode.IsA('vtkMRMLDisplayableNode') and desiredOutputNode.GetDisplayNode() is not None:
        desiredOutputNode.GetDisplayNode().SetVisibility(True)
      slicer.mrmlScene.RemoveNode(actualOutputNode)

    except Exception as e:
      msgbox = qt.QMessageBox()
      msgbox.setWindowTitle("Error running pipeline")
      msgbox.setText(str(e) + '\n\n' + "".join(traceback.TracebackException.from_exception(e).format()))
      msgbox.exec()
    finally:
      if self._runPipelineProgressDialog is not None:
        self._runPipelineProgressDialog.close()
        self._runPipelineProgressDialog = None

  def _modulesChanged(self):
    #update overall input/output
    self.ui.leInputType.text = self._moduleListWidget.getInputType()
    self.ui.leOutputType.text = self._moduleListWidget.getOutputType()

    testable = self._moduleListWidget.good() and self._moduleListWidget.count() > 0
    if testable:
      self.ui.lblTestInput.setVisible(self._moduleListWidget.getInputType() is not None)
      self.ui.cboxTestInput.setVisible(self._moduleListWidget.getInputType() is not None)
      if self._moduleListWidget.getInputType() is not None:
        self.ui.cboxTestInput.nodeTypes = (self._moduleListWidget.getInputType(), )

      self.ui.lblTestOutput.setVisible(self._moduleListWidget.getOutputType() is not None)
      self.ui.cboxTestOutput.setVisible(self._moduleListWidget.getOutputType() is not None)
      if self._moduleListWidget.getOutputType() is not None:
        self.ui.cboxTestOutput.nodeTypes = (self._moduleListWidget.getOutputType(), )
    else:
      self.ui.cboxTestInput.nodeTypes = ()
      self.ui.cboxTestOutput.nodeTypes = ()
    self.ui.cboxTestInput.enabled = testable
    self.ui.cboxTestOutput.enabled = testable
    self.ui.btnRun.enabled = testable

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()
    # if we don't clear this on cleanup, then the whole application segfaults during shutdown if
    # any CLI modules are still in the list
    self._moduleListWidget.clear()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # TODO Implement this

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    #TODO: Implement this

    self._parameterNode.EndModify(wasModified)

  def _runPipelineProgress(self, pipelineProgress):
    if self._runPipelineProgressDialog is not None:
      self._runPipelineProgressDialog.labelText = pipelineProgress.currentPipelinePieceName
      self._runPipelineProgressDialog.value = pipelineProgress.progress * 100
      slicer.app.processEvents()

#
# LegacyPipelineCreatorLogic
#

class LegacyPipelineCreatorLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  _allModules = []
  _defaultModulesLoaded = False
  _defaultModulesLock = threading.Lock()

  def __init__(self, useSingleton = True):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    If useSingleton is False, this class will have no loaded modules and can be used without affecting
    anything else. This is intended mainly for testing.
    """
    ScriptedLoadableModuleLogic.__init__(self)

    if useSingleton:
      self._allModules = LegacyPipelineCreatorLogic._allModules
      self.isSingletonParameterNode = True
    else:
      self._allModules = []
      self.isSingletonParameterNode = False

    self._pipeline = []
    self._runPipelineProgressCb = None

  
  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    #TODO: Implement this
    pass

  def resourcePath(self, filename):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(scriptedModulesPath, 'Resources', filename)

  @property
  def allModules(self):
    return self._allModules

  def registerModule(self, module):
    """
    Registers a module for use with the LegacyPipelineCreator
    """
    if not issubclass(module, PipelineInterface):
      raise TypeError("LegacyPipelineCreator registerModule argument must be a PipelineInterface")

    if module.GetName() in [x.GetName() for x in self.allModules]:
      raise Exception("Already registered module with the name '%s'" % module.GetName())

    lowerName = module.GetName().lower()
    for i in range(len(self._allModules)):
      if lowerName < self._allModules[i].GetName().lower():
        self._allModules.insert(i, module)
        break
    else:
      self._allModules.append(module)

  def runPipeline(self, modules, inputNode):
    """
    modules is [(moduleName, {module-parameter-name: module-parameter-value})]
     List of tuples. Each tuple is the module name and a dictionary of fixed parameters.
     Not all of the modules parameters need to be fixed.
    """
    replacements = self._makeReplacements("UnfinalizedPipeline", modules)
    moduleTemplateFile = os.path.join(self._getPipelineTemplateModulePath(), 'XXX.py.template')
    moduleCode = self._makeFileContent(moduleTemplateFile, replacements)

    #prevent the unfinalized pipeline from registering itself with the pipeline creator
    moduleCode = moduleCode.replace('@slicerPipeline', '# @slicerPipeline - unfinalized pipeline')

    localsDict = {}
    exec(moduleCode, globals(), localsDict)

    pipelineLogic = localsDict['%sLogic' % replacements['MODULE_NAME']]()
    pipelineLogic.SetProgressCallback(self._runPipelineProgress)
    return pipelineLogic.Run(inputNode)

  def setPipelineProgressCallback(self, cb):
    self._runPipelineProgressCb = cb

  def _runPipelineProgress(self, pipelineProgress):
    if self._runPipelineProgressCb is not None:
      self._runPipelineProgressCb(pipelineProgress)

  def _moduleExists(self, name):
    return name.lower() in [m.lower() for m in slicer.app.moduleManager().modulesNames()]

  def createPipeline(self, pipelineName, outputDirectory, modules):
    """
    modules is [(moduleName, {module-parameter-name: module-parameter-value})]
     List of tuples. Each tuple is the module name and a dictionary of fixed parameters.
     Not all of the modules parameters need to be fixed.
    """

    #do some up front checking to make sure we have everything we need
    errorStr = ""
    if not pipelineName.isidentifier() or keyword.iskeyword(pipelineName.lower()) or keyword.iskeyword(pipelineName):
      errorStr += " - Module name '%s' is not a valid pipeline module name\n" % (pipelineName + '/' + pipelineName.lower() if pipelineName else "")
      errorStr += "   Acceptable names start with a letter, contain only letters, numbers, and underscores, and cannot be a python keyword\n"

    if self._moduleExists(pipelineName):
      errorStr += " - Module name '%s' already exists. Note module names are effectively case insensitive.\n" % pipelineName

    if not modules:
      errorStr += " - Must have at least one module\n"

    if not outputDirectory:
      errorStr += " - Output directory must be specified\n"
    else:
      if not os.path.exists(outputDirectory):
        os.makedirs(outputDirectory)
      if os.listdir(outputDirectory):
        errorStr += " - Output directory must be empty or not exist yet\n"

    for index in range(len(modules)):
      if index > 0:
        module = self.moduleFromName(modules[index][0])
        prevModule = self.moduleFromName(modules[index - 1][0])
        if not prevModule:
          errorStr += " - Unknown pipeline module: '%s'\n" % modules[index - 1][0]
        if not module:
          errorStr += " - Unknown pipeline module: '%s'\n" % modules[index][0]
        if prevModule and module and prevModule.GetOutputType() != module.GetInputType():
          errorStr += " - Mismatched output to input type\n"
          errorStr += "   Between modules %d (%s) and %d (%s)\n" % (index-1, prevModule.GetName(), index, module.GetName())
          errorStr += "   %s != %s\n" % (prevModule.GetOutputType(), module.GetInputType())

    if errorStr:
      raise Exception("Error creating pipeline: \n" + errorStr)

    replacements = self._makeReplacements(pipelineName, modules)
    self._makeModule(outputDirectory, replacements)

  def _makeReplacements(self, pipelineName, modules):
    deps = ['LegacyPipelineCreator']
    for moduleName, _ in modules:
      module = self.moduleFromName(moduleName)
      deps += module.GetDependencies()
    deps = sorted(list(set(deps))) # Remove duplicates

    return {
      "MODULE_NAME": pipelineName,
      "MODULE_CATEGORIES": "['PipelineModules']", #TODO implement custom
      "MODULE_RUN_METHOD": self._createRunMethod(modules),
      "MODULE_COUNT": len(modules),
      "MODULE_DEPENDENCIES": str(deps),
      "MODULE_CONTRIBUTORS": "['LegacyPipelineCreator']", #TODO implement custom?
      "MODULE_SETUP_PIPELINE_UI_METHOD": self._createSetupPipelineUIMethod(modules),
      "MODULE_UPDATE_GUI_FROM_PARAMETER_NODE": "", #TODO implement as part of non-fixed parameters
      "MODULE_UPDATE_PARAMETER_NODE_FROM_GUI": "", #TODO implement as part of non-fixed parameters
      "MODULE_LOGIC_SET_METHODS": "", #TODO implement as part of non-fixed parameters
      "MODULE_INPUT_TYPE": self.moduleFromName(modules[0][0]).GetInputType(),
      "MODULE_OUTPUT_TYPE": self.moduleFromName(modules[-1][0]).GetOutputType(),
    }

  #this is anticipated to be needed for non-fixed parameters
  def _createSetupPipelineUIMethod(self, modules):
    ret = """
    def setupPipelineUI(self):
      pass
    """
    return textwrap.dedent(ret).strip()

  @staticmethod
  def fixUpParameterName(parameterName):
    newName = parameterName.replace(" ", "")
    if not newName.isidentifier():
      raise Exception("Invalid name: '%s'" % newName)
    return newName

  _beginningOfRunMethod='''
def Run(self, inputNode):
  nodes = [inputNode]
  currentPipelinePieceNumber=0
  def deleteIntermediates():
    if self.deleteIntermediates:
      shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
      for node in nodes[1:-1]:
        # Only remove if it is not the actual input or output.
        # This is possible if the first or last pipeline module did
        # shallow copy
        if node is not nodes[0] and node is not nodes[-1]:
          itemId = shNode.GetItemByDataNode(node)
          if itemId != 0:
            shNode.RemoveItem(itemId)
  try:
'''.lstrip('\n')

  _endOfRunMethod ='''
    self._Progress(nextPipelinePiece.GetName(), currentPipelinePieceNumber)
    deleteIntermediates()
    return nodes[-1]
  except:
    deleteIntermediates()
    raise
'''.lstrip('\n')

  def _createRunMethod(self, modules):
    methodText = self._beginningOfRunMethod
    for moduleName, parameters in modules:
      module = self.moduleFromName(moduleName)
      #the register doesn't really care if it gets a class or an instance, so handle both cases
      methodText += "    # {stringClass}\n".format(stringClass=str(module))
      methodText += "    nextPipelinePiece = pickle.loads({pickledClass})()\n".format(
          pickledClass=pickle.dumps(module),
        )
      methodText += "    self._Progress(nextPipelinePiece.GetName(), currentPipelinePieceNumber)\n"

      for parameterTup in parameters.items():
        if len(parameterTup) == 2:
          parameterName, parameterValue = parameterTup
        elif len(parameterTup) == 3:
          parameterName, _, parameterValue = parameterTup
        # we require parameter values to be pickleable, not stringable, but the strings
        # are nice when possible
        try:
          strValue = str(parameterValue)
        except:
          strValue = "<no string representation>"
        if isinstance(parameterValue, (int, str, float, bool)):
          #if the param can be set directly by the string representation of the class, do that for ease in reading
          #generated output.
          if isinstance(parameterValue, str):
            #if string add quotes
            strValue = '"%s"' % strValue
          methodText += "    nextPipelinePiece.Set{parameterName}({strValue})\n".format(
            parameterName=self.fixUpParameterName(parameterName),
            strValue=strValue,
          )
        else:
          #fallback to pickle method
          methodText += "    nextPipelinePiece.Set{parameterName}(pickle.loads({pickledValue})) # {strValue}\n".format(
              parameterName=self.fixUpParameterName(parameterName),
              pickledValue=pickle.dumps(parameterValue),
              strValue=strValue,
            )
      methodText += "    nodes.append(nextPipelinePiece.Run(nodes[-1]))\n"
      methodText += "    currentPipelinePieceNumber += 1\n\n"
    methodText += self._endOfRunMethod
    return methodText

  def moduleFromName(self, moduleName):
    print(moduleName, [x.GetName() for x in self.allModules])
    mods = [x for x in self.allModules if x.GetName() == moduleName]
    print(mods)
    if mods:
      return mods[0]
    return None

  def _makeModule(self, outputDirectory, replacements):
    """
    Makes a new pipeline module.
    outputDirectory is the output directory to make the module in. It must exist and should be empty.
    replacements is dictonary with expected keys
      MODULE_NAME - The name of the new module
      MODULE_CATEGORIES - Categories in the slicer the new module should show up in
      MODULE_DEPENDENCIES - Other modules this depends on
      MODULE_CONTRIBUTORS - Contributers
      MODULE_SETUP_PIPELINE_UI_METHOD - Python code to create UI. Expect first line to have no indentation.
        This function will take care of proper indentation
      MODULE_UPDATE_GUI_FROM_PARAMETER_NODE - Python code to update GUI from parameter node.
        Expect first line to have no indentation. This function will take care of proper indentation within the template file.
        You still need to do indentation on things like if statements or def methods.
      MODULE_UPDATE_PARAMETER_NODE_FROM_GUI - Python code to update parameter node from GUI.
        Expect first line to have no indentation. This function will take care of proper indentation within the template file.
        You still need to do indentation on things like if statements or def methods.
      MODULE_RUN_METHOD - Expect first line to have no indentation. This function will take care of proper indentation within the template file.
        You still need to do indentation on things like if statements or def methods.
      MODULE_LOGIC_SET_METHODS - Set of full python methods to set any parameters to the module.
        Expect first line to have no indentation. This function will take care of proper indentation within the template file.
        You still need to do indentation on things like if statements or def methods.
      MODULE_INPUT_TYPE - The modules input type
      MODULE_OUTPUT_TYPE - The modules output type
    """

    join = os.path.join
    normpath = os.path.normpath
    relpath = os.path.relpath
    pipelineTemplateModulePath = self._getPipelineTemplateModulePath()
    for rootdir, dirs, files in os.walk(pipelineTemplateModulePath):
      # Create any directories
      for directory in dirs:
        relativeDirectory = normpath(relpath(join(rootdir, directory), pipelineTemplateModulePath))
        outdir = join(outputDirectory, relativeDirectory)
        os.mkdir(outdir)

      # Copy all files
      for file in files:
        fullFilePath = join(rootdir, file)
        relativeFilePath = normpath(relpath(fullFilePath, pipelineTemplateModulePath)).replace('XXX', replacements['MODULE_NAME'])
        if not file.endswith('.template'):
          # If the filename doesn't end in .template, just copy as is
          outputFilePath = join(outputDirectory, relativeFilePath)
          shutil.copyfile(fullFilePath, outputFilePath)
        else:
          outputFilePath = join(outputDirectory, relativeFilePath[:-len('.template')])
          filledOutContent = self._makeFileContent(fullFilePath, replacements)
          with open(outputFilePath, 'w') as outFile:
            outFile.write(filledOutContent)

  def _getPipelineTemplateModulePath(self):
    return os.path.normpath(self.resourcePath('PipelineTemplateModule'))


  def _makeFileContent(self, filename, replacements):
    with open(filename, 'r') as inFile:
      content = inFile.read()
    templateString = ModuleTemplate(content)

    itemsThatNeedFixedIndentation = [
      'MODULE_SETUP_PIPELINE_UI_METHOD',
      'MODULE_RUN_METHOD',
      'MODULE_LOGIC_SET_METHODS',
      'MODULE_UPDATE_GUI_FROM_PARAMETER_NODE',
      'MODULE_UPDATE_PARAMETER_NODE_FROM_GUI',
    ]

    # deep copy the replacements dictionary so we aren't actually changing it
    replacementsCopy = copy.deepcopy(replacements)
    # Fixup indentation on the items we promised to
    for item in itemsThatNeedFixedIndentation:
      indentation = self._getIndentation(content, "{{" + item + "}}")
      replacementsCopy[item] = textwrap.indent(replacements[item], indentation)
      #we have indented everything, but the first line is already indented the .py
      #file, so unindent that
      replacementsCopy[item] = replacementsCopy[item][len(indentation):]

    filledOutContent = templateString.substitute(replacementsCopy)
    return filledOutContent


  @staticmethod
  def _getIndentation(content, lineContent):
    """
    Gets the indentation of the first line in content that has lineContent
    """
    for line in content.splitlines():
      loc = line.find(lineContent)
      if loc != -1:
        return line[:loc]
    return ""

#
# Free functions
#

def CallAfterAllTheseModulesLoaded(callback, modules):
  #if all modules are loaded
  if not set(modules).difference(set(slicer.app.moduleManager().modulesNames())):
    callback()
  else:
    def callbackWrapper():
      if not set(modules).difference(set(slicer.app.moduleManager().modulesNames())):
        callback()
        slicer.app.moduleManager().moduleLoaded.disconnect(callbackWrapper)
    slicer.app.moduleManager().moduleLoaded.connect(callbackWrapper)

def SingletonRegisterModule(module):
  """
  This method will handle correctly registering the module regardless of if
  the pipeline creator has already been loaded into slicer when it is called
  """
  def register():
      LegacyPipelineCreatorLogic().registerModule(module)
  dependencies = module.GetDependencies()
  dependencies.append('LegacyPipelineCreator')
  CallAfterAllTheseModulesLoaded(register, dependencies)

def slicerPipeline(module):
  """
  Class decorator to automatically register a class with the pipeline creator
  """
  if not issubclass(module, PipelineInterface):
    raise TypeError("A slicerPipeline must be a PipelineInterface: " + str(module.__name__))
  SingletonRegisterModule(module)
  return module
