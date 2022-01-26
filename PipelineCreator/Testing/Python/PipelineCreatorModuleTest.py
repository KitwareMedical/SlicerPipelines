import os
import tempfile
import textwrap
import qt

import slicer
import vtk
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleTest
from PipelineCreator import PipelineCreatorLogic
from PipelineCreatorLib.PipelineBases import PipelineInterface, ProgressablePipeline


# these tests are bad because they leave pipeline modules hanging around,
# but I didn't see a good way to unload single modules
_pipelineNameCounter = 0
# not thread safe
def nextPipelineName():
  global _pipelineNameCounter
  _pipelineNameCounter += 1
  return "PipelineCreatorModuleTest_Pipeline" + str(_pipelineNameCounter)

def loadModule(name, path):
  factory = slicer.app.moduleManager().factoryManager()
  factory.registerModule(qt.QFileInfo(os.path.join(path, name + ".py")))
  factory.loadModules([name])

def getLogic(pipelineName):
  codeToRun = textwrap.dedent('''
    from {pipelineName} import {pipelineName}Logic
    logic = {pipelineName}Logic()
    ''').strip().format(
      pipelineName=pipelineName,
    )
  localsParam = {}
  exec(codeToRun, {}, localsParam)
  return localsParam['logic']

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
    return ['Models']

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
    return ['Segmentations']

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

  def test_PipelineCreatorLogic_createPipeline1(self):
    for doMesh in (True, False):
      logic = self.createTesterPipelineCreator()
      pipeline = [
        ("TestPipeline1", {}),
        ("TestPipeline2", {"HasMesh": doMesh}),
      ]
      pipelineName = nextPipelineName()

      with tempfile.TemporaryDirectory(dir=slicer.app.temporaryPath) as pipelineDir:
        # make the pipeline
        self.assertFalse(os.listdir(pipelineDir))
        logic.createPipeline(pipelineName, pipelineDir, pipeline)

        # make sure we got something
        self.assertTrue(os.listdir(pipelineDir))
        loadModule(pipelineName, pipelineDir)

        # load it
        self.assertIn(pipelineName, slicer.app.moduleManager().modulesNames())
        pipelineModule = slicer.app.moduleManager().module(pipelineName)
        self.assertIsNotNone(pipelineModule)

        # make sure it runs
        logic = getLogic(pipelineName)
        inputNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        output = logic.Run(inputNode)
        self.assertIsInstance(output, slicer.vtkMRMLModelNode)
        if doMesh:
          self.assertIsNotNone(output.GetMesh())
        else:
          self.assertIsNone(output.GetMesh())

        # we expect created pipelines to be PipelineInterface
        self.assertIsInstance(logic, PipelineInterface)

        # we expect dependencies to be a union of all pieces + pipelineCreator
        expectedDepends = {'PipelineCreator', 'Models', 'Segmentations'}
        self.assertEqual(expectedDepends, set(logic.GetDependencies()))

        # check most of PipelineInterface
        self.assertEqual(pipelineName, logic.GetName())
        self.assertEqual('vtkMRMLModelNode', logic.GetInputType())
        self.assertEqual('vtkMRMLModelNode', logic.GetOutputType())
        self.assertEqual([], logic.GetParameters())
