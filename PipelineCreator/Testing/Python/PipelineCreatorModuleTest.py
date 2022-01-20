import qt

import slicer
import vtk
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleTest
from PipelineCreator import PipelineCreatorLogic
from PipelineCreatorLib.PipelineBases import PipelineInterface, ProgressablePipeline

class Parameter(object):
  def __init__(self):
    self._ui = qt.QSpinBox() # doesn't really matter
    self.value = 0

  def GetUI(self):
    return self._ui

  def GetValue(self):
    return self.value

class TestPipeline1(PipelineInterface):
  @staticmethod
  def GetName():
    return "TestPipeline1"

  @staticmethod
  def GetParameters():
    []

  @staticmethod
  def GetInputType():
    return "vtkMRMLModelNode"

  @staticmethod
  def GetOutputType():
    return "vtkMRMLSegmentationNode"

  @staticmethod
  def GetDependencies():
    return []

  def Run(self, inputNode):
    return slicer.mrmlScene.AddNewNodeByClass(self.GetOutputType())

  def SetProgressCallback(self, cb):
    pass

class TestPipeline2(ProgressablePipeline):
  def __init__(self):
    super().__init__()
    self.hasMesh = False
    self.param2 = 0

  def SetHasMesh(self, value):
    self.hasMesh = value
  def SetParam2(self, value):
    self.param2 = value

  @staticmethod
  def GetName():
    return "TestPipeline2"

  @staticmethod
  def GetParameters():
    return [
      ("HasMesh", Parameter()),
      ("Param2", "param 2 label", Parameter()),
    ]

  @staticmethod
  def GetInputType():
    return "vtkMRMLSegmentationNode"

  @staticmethod
  def GetOutputType():
    return "vtkMRMLModelNode"

  @staticmethod
  def GetDependencies():
    return []

  def Run(self, inputNode):
    output = slicer.mrmlScene.AddNewNodeByClass(self.GetOutputType())
    if self.hasMesh:
      output.SetAndObserveMesh(vtk.vtkPolyData())
    return output

  def SetProgressCallback(self, cb):
    pass

  def GetNumberOfPieces():
    return 1

#
# PipelineCreatorTest
#

class PipelineCreatorModuleTest(ScriptedLoadableModuleTest):
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
    # self.setUp()
    pass

  def test_PipelineCreatorLogic_register1(self):
    """
    Given an empty PipelineCreatorLogic,
    When I register a new pipeline module,
    Then I can see the module is registered
    """
    logic = PipelineCreatorLogic(useSingleton=False)
    self.assertEqual(0, len(logic.allModules))
    logic.registerModule(TestPipeline1)
    self.assertEqual(1, len(logic.allModules))
    self.assertIn(TestPipeline1, logic.allModules)

  def test_PipelineCreatorLogic_register2(self):
    """
    Given an empty PipelineCreatorLogic,
    When I register a new pipeline module,
    Then I can see the module is registered
    """
    logic = PipelineCreatorLogic(useSingleton=False)
    logic.registerModule(TestPipeline1)
    logic.registerModule(TestPipeline2)
    self.assertIn(TestPipeline1, logic.allModules)
    self.assertIn(TestPipeline2, logic.allModules)

  def createTesterPipelineCreator(self):
    logic = PipelineCreatorLogic(useSingleton=False)
    logic.registerModule(TestPipeline1)
    logic.registerModule(TestPipeline2)
    return logic

  def test_PipelineCreatorLogic_runPipeline1(self):
    logic = self.createTesterPipelineCreator()

    pipeline = [("TestPipeline1", {})]
    inputNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')

    output = logic.runPipeline(pipeline, inputNode)

    self.assertIsInstance(output, slicer.vtkMRMLSegmentationNode)

  def test_PipelineCreatorLogic_runPipeline2(self):
    logic = self.createTesterPipelineCreator()

    pipeline = [
      ("TestPipeline1", {}),
      ("TestPipeline2", {}),
    ]
    inputNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')

    output = logic.runPipeline(pipeline, inputNode)

    self.assertIsInstance(output, slicer.vtkMRMLModelNode)

  def test_PipelineCreatorLogic_runPipeline3(self):
    logic = self.createTesterPipelineCreator()

    pipeline = [
      ("TestPipeline1", {}),
      ("TestPipeline2", {"HasMesh": False}),
    ]
    inputNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
    output = logic.runPipeline(pipeline, inputNode)
    self.assertIsInstance(output, slicer.vtkMRMLModelNode)
    self.assertIsNone(output.GetMesh())

  def test_PipelineCreatorLogic_runPipeline4(self):
    logic = self.createTesterPipelineCreator()

    pipeline = [
      ("TestPipeline1", {}),
      ("TestPipeline2", {"HasMesh": True}),
    ]
    inputNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
    output = logic.runPipeline(pipeline, inputNode)
    self.assertIsInstance(output, slicer.vtkMRMLModelNode)
    self.assertIsNotNone(output.GetMesh())
