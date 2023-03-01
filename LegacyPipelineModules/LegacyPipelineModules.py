import os
import slicer
from LegacyPipelineCreator import LegacyPipelineCreatorLogic
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#import all the default wrappings. doing the import will register them with the pipeline creator
from LegacyPipelineModulesLib import (
  CLIModuleWrapping,
  PipelineParameters,
  SegmentationsWrapping,
  SegmentEditorWrapping,
  SurfaceToolboxWrapping,
  VolumesWrapping,
  vtkFilterJSONReader,
)

#note: if ModelMaker is not actually in the system, then this call will have no effect
CLIModuleWrapping.PipelineCLI("ModelMaker", LegacyPipelineCreatorLogic(), excludeArgs=['ColorTable', 'ModelHierarchyFile'])

#
# LegacyPipelineModules
#

class LegacyPipelineModules(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Legacy Pipeline Modules"
    self.parent.categories = ["Pipelines.Advanced"]
    self.parent.dependencies = [
      "LegacyPipelineCLIBridge",
      "LegacyPipelineCreator",
      "SegmentEditor",
    ]
    self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This module exists to create pipelines for the LegacyPipelineCreator to use.
"""
    self.parent.acknowledgementText = "This module was originally developed by Connor Bowley (Kitware, Inc.) for SlicerSALT."
    self.parent.hidden = True

#
# LegacyPipelineModulesLogic
#

class LegacyPipelineModulesLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def loadVTKJSON(self, legacyPipelineCreatorLogic):
    vtkFilterJSONReader.RegisterLegacyPipelineModules(legacyPipelineCreatorLogic, self.resourcePath('PipelineVTKFilterJSON'))

  def resourcePath(self, filename):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(scriptedModulesPath, 'Resources', filename)

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

#
# LegacyPipelineModulesTest
#

class LegacyPipelineModulesTest(ScriptedLoadableModuleTest):
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
    self.test_LegacyPipelineModules1()

  def test_LegacyPipelineModules1(self):
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
  LegacyPipelineModulesLogic().loadVTKJSON(LegacyPipelineCreatorLogic())

#load the vtk json files when able
try:
  slicer.modules.legacypipelinemodules
  _load()
except AttributeError:
  def callback(moduleName):
    if "LegacyPipelineModules" == moduleName:
      _load()
  slicer.app.moduleManager().moduleLoaded.connect(callback)
