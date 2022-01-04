import os
import slicer
from PipelineCreator import PipelineCreatorLogic
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#import all the default wrappings. doing the import will register them with the pipeline creator
from PipelineModulesLib import (
  CLIModuleWrapping,
  PipelineParameters,
  SegmentationsWrapping,
  SegmentEditorWrapping,
  SurfaceToolboxWrapping,
  vtkFilterJSONReader,
)

#
# PipelineModules
#

class PipelineModules(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Pipeline Modules"
    self.parent.categories = ["Pipelines.Advanced"]
    self.parent.dependencies = [
      "MeshToLabelMap",
      "PipelineCLIBridge",
      "PipelineCreator",
      "SegmentEditor",
    ]
    self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This module exists to create pipelines for the PipelineCreator to use.
"""
    self.parent.acknowledgementText = ""
    self.parent.hidden = True

#
# PipelineModulesLogic
#

class PipelineModulesLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def loadVTKJSON(self, pipelineCreatorLogic):
    vtkFilterJSONReader.RegisterPipelineModules(pipelineCreatorLogic, self.resourcePath('PipelineVTKFilterJSON'))

  def loadCLIModules(self, pipelineCreatorLogic):
    #important that all modules in here show up as dependencies in PipelineModules class
    CLIModuleWrapping.PipelineCLI(slicer.modules.meshtolabelmap, pipelineCreatorLogic, "mesh", excludeArgs=['reference'])

  def resourcePath(self, filename):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(scriptedModulesPath, 'Resources', filename)

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

#
# PipelineModulesTest
#

class PipelineModulesTest(ScriptedLoadableModuleTest):
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
    self.test_PipelineModules1()

  def test_PipelineModules1(self):
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
    #TODO: tests for pipelines created by this module
    pass

def _load():
  pipelineCreator = PipelineCreatorLogic()
  pipelineModules = PipelineModulesLogic()

  pipelineModules.loadVTKJSON(pipelineCreator)
  pipelineModules.loadCLIModules(pipelineCreator)

#load the vtk json files when able
try:
  slicer.modules.pipelinemodules
  _load()
except AttributeError:
  def callback(moduleName):
    if "PipelineModules" == moduleName:
      _load()
  slicer.app.moduleManager().moduleLoaded.connect(callback)
