import collections
import copy
import inspect
import keyword
import os
import pickle
import shutil
import textwrap
import threading
from string import Template

import ctk
import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

from Widgets.SelectModulePopUp import SelectModulePopUp

#
# ModuleTemplate
#
class ModuleTemplate(Template):
  """
  Custom template class with special syntax
  because CMake's variable syntax is the same
  as the default Template's replace syntax
  """
  delimiter = '{{'
  # only really want braced, but need both groups "named" and "braced" to exist
  pattern = r"""\{\{(?:
    (?P<escaped>\{) |
    (?P<named>[_a-z][_a-z0-9]*)}} |
    (?P<braced>[_a-z][_a-z0-9]*)}} |
    (?P<invalid>)
  )"""

#
# PipelineCreator
#

class PipelineCreator(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Pipeline Creator"
    self.parent.categories = ["Pipelines"]
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
    self.parent.helpText = """
This is module offers the ability to create simple modules (aka pipelines) via a GUI interface with no coding knowledge needed
See more information in <a href="https://github.com/KitwareMedical/SlicerPipelines/blob/main/README.md">module documentation</a>.
"""
    self.parent.acknowledgementText = """
This module was originally developed by Connor Bowley, Kitware Inc.
"""

  def createLogic(self):
    return PipelineCreatorLogic()


class _ModuleButtonHolder:
  pass

#
# PipelineCreatorWidget
#

class PipelineCreatorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
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
    self._moduleButtons = []

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/PipelineCreator.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)
    self.uiLayout = self.uiWidget.layout()

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    self.uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = PipelineCreatorLogic()

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

    #insert first insert button
    self._moduleUiStartIndex = self.uiLayout.count() - 1 # - 1 because we want to keep the vertical spacer as the last item

    insertButton = qt.QPushButton()
    insertButton.setText("Insert Module")
    insertButton.clicked.connect(lambda: self._onInsertModuleButton(0))
    # Note: self._moduleUiStartInded is still correct after this insert because this button will always be below
    # the modules
    self.uiLayout.insertWidget(self._moduleUiStartIndex, insertButton)

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
      for buttonHolder in self._moduleButtons:
        #remove from UI
        buttonHolder.cbutton.hide()
        self.uiLayout.removeWidget(buttonHolder.cbutton)
      self._moduleButtons.clear()
      self._modulesChanged()

  def _convertModuleButtonsToLogicInput(self):
    return [
        (b.module.name, {
          paramName: param.GetValue() for paramName, param in b.parameters #TODO if param is fixed
        }) for b in self._moduleButtons
      ]


  def _onFinalize(self):
    try:
      modules = self._convertModuleButtonsToLogicInput()
      moduleName = self.ui.leModuleName.text
      outputDirectory = self.ui.leOutputDirectory.text
      self.logic.createPipeline(moduleName, outputDirectory, modules)
      msgbox = qt.QMessageBox()
      msgbox.setWindowTitle("SUCCESS")
      msgbox.setText("Successfully created Pipeline '%s' at '%s'!" % (moduleName, outputDirectory))
      msgbox.exec()
    except Exception as e:
      msgbox = qt.QMessageBox()
      msgbox.setWindowTitle("Error creating pipeline")
      msgbox.setText(str(e))
      msgbox.exec()

  def _onRun(self):
    modules = self._convertModuleButtonsToLogicInput()
    inputNode = self.ui.cboxTestInput.currentNode()
    actualOutputNode = self.logic.runPipeline(modules, inputNode)

    desiredOutputNode = self.ui.cboxTestOutput.currentNode()
    if desiredOutputNode is not None:
      # copy into node, but keep name
      name = desiredOutputNode.GetName()
      desiredOutputNode.Copy(actualOutputNode)
      desiredOutputNode.SetName(name)
    slicer.mrmlScene.RemoveNode(actualOutputNode)
    if not desiredOutputNode.GetDisplayNode():
      desiredOutputNode.CreateDefaultDisplayNodes()

    inputNode.GetDisplayNode().SetVisibility(False)
    desiredOutputNode.GetDisplayNode().SetVisibility(True)

  def _modulesChanged(self):
    testable = self._verifyInputOutputFlow() and self._moduleButtons
    if testable:
      self.ui.cboxTestInput.nodeTypes = (self._moduleButtons[0].module.inputType, )
      self.ui.cboxTestOutput.nodeTypes = (self._moduleButtons[-1].module.outputType, )
    else:
      self.ui.cboxTestInput.nodeTypes = ()
      self.ui.cboxTestOutput.nodeTypes = ()
    self.ui.cboxTestInput.enabled = testable
    self.ui.cboxTestOutput.enabled = testable
    self.ui.btnRun.enabled = testable

  def _verifyInputOutputFlow(self):
    #update overall input/output
    if self._moduleButtons:
      self.ui.leInputType.text = self._moduleButtons[0].module.inputType
      self.ui.leOutputType.text = self._moduleButtons[-1].module.outputType

    #check each input and output and color if good or bad
    lineEdit = qt.QLineEdit()
    defaultPalette = lineEdit.palette

    badPalette = qt.QPalette()
    badPalette.setColor(qt.QPalette.Base, qt.QColor(255, 128, 128))

    good = True
    for index, curButtonHolder in enumerate(self._moduleButtons):
      curModule = curButtonHolder.module
      if index == 0:
        curButtonHolder.inputTypeLineEdit.setPalette(defaultPalette)
      elif index > 0:
        prevButtonHolder = self._moduleButtons[index - 1]
        prevModule = prevButtonHolder.module
        if curModule.inputType != prevModule.outputType:
          curButtonHolder.inputTypeLineEdit.setPalette(badPalette)
          prevButtonHolder.outputTypeLineEdit.setPalette(badPalette)
          good = False
        else:
          curButtonHolder.inputTypeLineEdit.setPalette(defaultPalette)
          prevButtonHolder.outputTypeLineEdit.setPalette(defaultPalette)

      if index == len(self._moduleButtons) - 1:
        curButtonHolder.outputTypeLineEdit.setPalette(defaultPalette)
    return good

  def _onDeleteModule(self, buttonHolder):
    q = qt.QMessageBox()
    q.setWindowTitle("Deleting module")
    q.setText("Are you sure you want to delete module '%s'?" % buttonHolder.module.name)
    q.addButton(qt.QMessageBox.Yes)
    q.addButton(qt.QMessageBox.No)

    if q.exec() == qt.QMessageBox.Yes:
      buttonHolder.cbutton.hide()
      self.uiLayout.removeWidget(buttonHolder.cbutton)
      self._moduleButtons.remove(buttonHolder)
      self._modulesChanged()

  def _onModuleMoveUp(self, buttonHolder):
    self._onModuleMove(buttonHolder, -1)

  def _onModuleMoveDown(self, buttonHolder):
    self._onModuleMove(buttonHolder, 1)

  def _onModuleMove(self, buttonHolder, movement):
    index = self._moduleButtons.index(buttonHolder)
    if 0 <= index + movement < len(self._moduleButtons):
      buttonHolder.cbutton.hide()
      self._moduleButtons.pop(index)
      self._moduleButtons.insert(index + movement, buttonHolder)
      self.uiLayout.removeWidget(buttonHolder.cbutton)
      self.uiLayout.insertWidget(self._moduleUiStartIndex + index + movement, buttonHolder.cbutton)
      buttonHolder.cbutton.show()
      self._modulesChanged()

  def _onInsertModuleButton(self, listIndex):
    popUp = SelectModulePopUp(self.logic.allModules, None, self.uiWidget)
    popUp.accepted.connect(lambda: self._onPopUpAccepted(popUp))
    popUp.open()

  def _onPopUpAccepted(self, popUp):
    try:
      module = popUp.chosenModule
      popUp.close()
      popUp.destroy()

      buttonHolder = _ModuleButtonHolder()
      cbutton = ctk.ctkCollapsibleButton()
      cbutton.setText(module.name)
      cbutton.collapsed = False

      hlayout = qt.QHBoxLayout()
      cbutton.setLayout(hlayout)
      
      buttonVLayout = qt.QVBoxLayout()
      hlayout.addLayout(buttonVLayout)
      upButton = qt.QPushButton("↑")
      upButton.clicked.connect(lambda: self._onModuleMoveUp(buttonHolder))
      deleteButton = qt.QPushButton("X")
      deleteButton.clicked.connect(lambda: self._onDeleteModule(buttonHolder))
      downButton = qt.QPushButton("↓")
      downButton.clicked.connect(lambda: self._onModuleMoveDown(buttonHolder))
      buttonVLayout.addWidget(upButton)
      buttonVLayout.addWidget(deleteButton)
      buttonVLayout.addWidget(downButton)

      #input type
      moduleFormLayout = qt.QFormLayout()
      hlayout.addLayout(moduleFormLayout)
      inputTypeLabel = qt.QLabel("Input Type:")
      inputTypeLineEdit = qt.QLineEdit(module.inputType)
      inputTypeLineEdit.setReadOnly(True)
      moduleFormLayout.addRow(inputTypeLabel, inputTypeLineEdit)

      #parameters
      buttonHolder.parameters = module.MakeParameters()
      for name, param in buttonHolder.parameters:
        try:
          moduleFormLayout.addRow(name + ":", param.GetUI())
        except Exception as e:
          raise Exception ("Exception trying to create parameter: '%s' for module '%s'\n    %s"
            % (name, module.name, str(e)))

      #output type
      outputTypeLabel = qt.QLabel("Output Type:")
      outputTypeLineEdit = qt.QLineEdit(module.outputType)
      outputTypeLineEdit.setReadOnly(True)
      moduleFormLayout.addRow(outputTypeLabel, outputTypeLineEdit)

      if not self._moduleButtons:
        index = 0
      else:
        index = len(self._moduleButtons)

      buttonHolder.module = module
      buttonHolder.cbutton = cbutton
      buttonHolder.inputTypeLineEdit = inputTypeLineEdit
      buttonHolder.outputTypeLineEdit = outputTypeLineEdit
      self._moduleButtons.insert(index, buttonHolder)
      self.uiLayout.insertWidget(self._moduleUiStartIndex + index, cbutton)

      self._modulesChanged()
    except Exception as e:
          print ("Exception trying add module: '%s' for module '%s'\n    %s"
            % (name, module.name, str(e)))
          raise

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

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

class _ModuleHolder:
  def __init__(self, module = None):
    self._module = module

  @property
  def name(self):
    try:
      return self._module.GetName()
    except TypeError:
      return self._module().GetName()

  @property
  def inputType(self):
    try:
      return self._module.GetInputType()
    except TypeError:
      return self._module().GetInputType()

  @property
  def outputType(self):
    try:
      return self._module.GetOutputType()
    except TypeError:
      return self._module().GetOutputType()

  @property
  def dependencies(self):
    try:
      return self._module.GetDependencies()
    except TypeError:
      return self._module().GetDependencies()

  @property
  def moduleClass(self):
    return self._module if inspect.isclass(self._module) else self._module.__class__

  def moduleInstance(self):
    return self._module if not inspect.isclass(self._module) else self._module()

  def MakeParameters(self):
    try:
      return self._module.GetParameters()
    except TypeError:
      return self._module().GetParameters()

  def updateParameterNodeFromSelf(self, param):
    param.SetParameter('name', self.name)
    param.SetParameter('inputType', self.inputType)
    param.SetParameter('outputType', self.outputType)
    #TODO: implement this

  def updateSelfFromParameterNode(self, param):
    #TODO: implement this
    pass

  def __str__(self) -> str:
    return self.name

  def __repr__(self):
    return self.__str__()


#
# PipelineCreatorLogic
#

class PipelineCreatorLogic(ScriptedLoadableModuleLogic):
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
      self._allModules = PipelineCreatorLogic._allModules
      self.isSingletonParameterNode = True
    else:
      self._allModules = {}
      self.isSingletonParameterNode = False

    self._pipeline = []

  
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
    Registers a module for use with the PipelineCreator
    """
    if module.GetName() in [x.name for x in self.allModules]:
      raise Exception("Already registered module with the name '%s'" % module.GetName())

    lowerName = module.GetName().lower()
    for i in range(len(self._allModules)):
      if lowerName < self._allModules[i].name.lower():
        self._allModules.insert(i, _ModuleHolder(module))
        break
    else:
      self._allModules.append(_ModuleHolder(module))

  def runPipeline(self, modules, inputNode):
    """
    modules is [(moduleName, {module-parameter-name: module-parameter-value})]
     List of tuples. Each tuple is the module name and a dictionary of fixed parameters.
     Not all of the modules parameters need to be fixed.
    """
    runMethodAsString = self._createRunMethod(modules)
    localsDict = {}
    exec(runMethodAsString, globals(), localsDict)

    fakeModule = collections.namedtuple("FakeModule", "deleteIntermediates")
    fakeSelf = fakeModule(deleteIntermediates=True)
    return localsDict["Run"](fakeSelf, inputNode)

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
        if prevModule and module and prevModule.outputType != module.inputType:
          errorStr += " - Mismatched output to input type\n"
          errorStr += "   Between modules %d (%s) and %d (%s)\n" % (index-1, prevModule.name, index, module.name)
          errorStr += "   %s != %s\n" % (prevModule.outputType, module.inputType)

    if errorStr:
      raise Exception("Error creating pipeline: \n" + errorStr)

    deps = ['PipelineCreator']
    for moduleName, _ in modules:
      module = self.moduleFromName(moduleName)
      deps += module.dependencies
    deps = sorted(list(set(deps))) # Remove duplicates

    replacements = {
      "MODULE_NAME": pipelineName,
      "MODULE_CATEGORIES": "['PipelineModules']", #TODO implement custom
      "MODULE_RUN_METHOD": self._createRunMethod(modules),
      "MODULE_DEPENDENCIES": str(deps),
      "MODULE_CONTRIBUTORS": "['PipelineCreator']", #TODO implement custom?
      "MODULE_SETUP_PIPELINE_UI_METHOD": self._createSetupPipelineUIMethod(modules),
      "MODULE_UPDATE_GUI_FROM_PARAMETER_NODE": "", #TODO implement as part of non-fixed parameters
      "MODULE_UPDATE_PARAMETER_NODE_FROM_GUI": "", #TODO implement as part of non-fixed parameters
      "MODULE_LOGIC_SET_METHODS": "", #TODO implement as part of non-fixed parameters
      "MODULE_INPUT_TYPE": self.moduleFromName(modules[0][0]).inputType,
      "MODULE_OUTPUT_TYPE": self.moduleFromName(modules[-1][0]).outputType,
    }

    self._makeModule(outputDirectory, replacements)

  def _createSetupPipelineUIMethod(self, modules):
    inputType = self.moduleFromName(modules[0][0]).inputType
    outputType = self.moduleFromName(modules[-1][0]).outputType
    ret = """
    def setupPipelineUI(self):
      self.ui.InputNodeComboBox.nodeTypes = ('{inputType}', ) # Need the comma so it doesn't split each character
      self.ui.OutputNodeComboBox.nodeTypes = ('{outputType}', ) # Need the comma so it doesn't split each character
    """.format(
      inputType=inputType,
      outputType=outputType,
    )
    return textwrap.dedent(ret).strip()

  @staticmethod
  def fixUpParameterName(parameterName):
    newName = parameterName.replace(" ", "")
    if not newName.isidentifier():
      raise Exception("Invalid name: '%s'" % newName)
    return newName

  def _createRunMethod(self, modules):
    methodText = "def Run(self, inputNode):\n" + \
                 "  nodes = [inputNode]\n"
    for moduleName, parameters in modules:
      moduleHolder = self.moduleFromName(moduleName)
      #the register doesn't really care if it gets a class or an instance, so handle both cases
      methodText += "  # {stringClass}\n".format(stringClass=str(moduleHolder.moduleClass))
      methodText += "  nextPipelinePiece = pickle.loads({pickledClass})()\n".format(
          pickledClass=pickle.dumps(moduleHolder.moduleClass),
        )

      for parameterName, parameterValue in parameters.items():
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
          methodText += "  nextPipelinePiece.Set{parameterName}({strValue})\n".format(
            parameterName=self.fixUpParameterName(parameterName),
            strValue=strValue,
          )
        else:
          #fallback to pickle method
          methodText += "  nextPipelinePiece.Set{parameterName}(pickle.loads({pickledValue})) # {strValue}\n".format(
              parameterName=self.fixUpParameterName(parameterName),
              pickledValue=pickle.dumps(parameterValue),
              strValue=strValue,
            )
      methodText += "  nodes.append(nextPipelinePiece.Run(nodes[-1]))\n\n"
    methodText += "  if self.deleteIntermediates:\n" + \
                  "    for node in nodes[1:-1]:\n" + \
                  "      # Only remove if it is not the actual input or output.\n" + \
                  "      # This is possible if the first or last pipeline module did\n" + \
                  "      # shallow copy\n" + \
                  "      if node is not nodes[0] and node is not nodes[-1]:\n" + \
                  "        slicer.mrmlScene.RemoveNode(node)\n\n" + \
                  "  return nodes[-1]\n"
    return methodText

  def moduleFromName(self, moduleName):
    mods = [x for x in self.allModules if x.name == moduleName]
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
      MODULE_RUN_METHOD - Body of run method.
        Expect first line to have no indentation. This function will take care of proper indentation within the template file.
        You still need to do indentation on things like if statements or def methods.
      MODULE_LOGIC_SET_METHODS - Set of full python methods to set any parameters to the module.
        Expect first line to have no indentation. This function will take care of proper indentation within the template file.
        You still need to do indentation on things like if statements or def methods.
      MODULE_INPUT_TYPE - The modules input type
      MODULE_OUTPUT_TYPE - The modules output type
    """
    replacementsCopy = copy.deepcopy(replacements)
    itemsThatNeedFixedIndentation = [
      'MODULE_SETUP_PIPELINE_UI_METHOD',
      'MODULE_RUN_METHOD',
      'MODULE_LOGIC_SET_METHODS',
      'MODULE_UPDATE_GUI_FROM_PARAMETER_NODE',
      'MODULE_UPDATE_PARAMETER_NODE_FROM_GUI',
    ]

    join = os.path.join
    normpath = os.path.normpath
    relpath = os.path.relpath
    pipelineTemplateModulePath = normpath(self.resourcePath('PipelineTemplateModule'))
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
          with open(fullFilePath, 'r') as inFile:
            content = inFile.read()
            templateString = ModuleTemplate(content)

          # Fixup indentation on the items we promised to
          for item in itemsThatNeedFixedIndentation:
            indentation = self._getIndentation(content, "{{" + item + "}}")
            replacementsCopy[item] = textwrap.indent(replacements[item], indentation)
            #we have indented everything, but the first line is already indented the .py
            #file, so unindent that
            replacementsCopy[item] = replacementsCopy[item][len(indentation):]

          filledOutContent = templateString.substitute(replacementsCopy)
          with open(outputFilePath, 'w') as outFile:
            outFile.write(filledOutContent)


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
# PipelineCreatorTest
#

class PipelineCreatorTest(ScriptedLoadableModuleTest):
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
    self.test_PipelineCreator1()

  def test_PipelineCreator1(self):
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

    self.delayDisplay("Starting the test. Need to write tests")

    #TODO create tests

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

def SingletonRegisterModule(module, moduleDependencies = None):
  """
  This method will handle correctly registering the module regardless of if
  the pipeline creator has already been loaded into slicer when it is called
  """
  def register():
    try:
      PipelineCreatorLogic().registerModule(module)
    except TypeError:
      PipelineCreatorLogic().registerModule(module())
  dependencies = moduleDependencies or []
  dependencies.append('PipelineCreator')
  CallAfterAllTheseModulesLoaded(register, dependencies)

def slicerPipeline(classVar):
  """
  Class decorator to automatically register a class with the pipeline creator
  """
  try:
    dependencies = classVar.GetDependencies()
  except AttributeError:
    dependencies = []

  SingletonRegisterModule(classVar, dependencies)
  return classVar
