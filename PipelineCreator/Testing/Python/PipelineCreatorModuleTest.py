import importlib
import os
import pickle  # this shows as unused but is used by test_cleanType during the eval
import sys
import tempfile
from typing import Annotated
import unittest

import networkx as nx

import qt

import slicer
import vtk

from slicer.parameterNodeWrapper import (
    findChildWidgetForParameter,
    parameterPack,
    Decimals,
    Default,
    Minimum,
    SingleStep,
    WithinRange,
)

from slicer import (
    vtkMRMLLabelMapVolumeNode,
    vtkMRMLModelNode,
    vtkMRMLScalarVolumeNode,
    vtkMRMLSegmentationNode,
)

from PipelineCreator import PipelineCreatorLogic
from _PipelineCreator import PipelineCreation

class TempPythonModule:
    def __init__(self, codeAsString):
        self.codeAsString = codeAsString

    def __enter__(self):
        # load the generated code into a temporary module
        # https://stackoverflow.com/a/60054279
        spec = importlib.util.spec_from_loader('tempModule', loader=None)
        self.tempModule = importlib.util.module_from_spec(spec)
        sys.modules['tempModule'] = self.tempModule
        exec(self.codeAsString, self.tempModule.__dict__)
        return self.tempModule
    
    def __exit__(self, type, value, traceback):
        sys.modules.pop('tempModule')

def findChildWithProperty(widget, property, propertyValue):
    for child in widget.findChildren(qt.QObject):
        if child.property(property) == propertyValue:
            return child
    return None

# Not actually running anything in these tests, so the implementation
# doesn't matter, only the signature.
# Cannot pickle local functions, so need these at the global scope
def passthru(mesh: vtkMRMLModelNode) -> vtkMRMLModelNode:
    return mesh

def centerOfX(mesh: vtkMRMLModelNode) -> float:
    """
    The tests aren't relying on this actual computation, just the signature going from
    MRMLNode to non-MRMLNode
    """
    pass

def decimation(mesh: vtkMRMLModelNode,
               reduction: Annotated[float, WithinRange(0, 1)]) -> vtkMRMLModelNode:
    decimate = vtk.vtkQuadricDecimation()
    decimate.SetTargetReduction(reduction)
    decimate.SetInputData(mesh.GetPolyData())
    decimate.Update()
    model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    model.SetAndObserveMesh(decimate.GetOutput())
    return model

def translate(mesh: vtkMRMLModelNode,
              x: float,
              y: float,
              z: float) -> vtkMRMLModelNode:
    transform = vtk.vtkTransform()
    transform.Translate(x, y, z)
    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetTransform(transform)
    transformFilter.SetInputData(mesh.GetPolyData())
    transformFilter.Update()
    model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    model.SetAndObserveMesh(transformFilter.GetOutput())
    return model

def makeSphereModel(self):
    sphereSource = vtk.vtkSphereSource()
    sphereSource.Update()
    model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    model.SetAndObserveMesh(sphereSource.GetOutput())
    self.assertEqual(model.GetMesh().GetCenter(), (0.0, 0.0, 0.0))
    return model

@parameterPack
class SegmentationAndReferenceVolume:
    segmentation: vtkMRMLSegmentationNode
    referenceVolume: vtkMRMLScalarVolumeNode

# test a very real world pipeline that was causing issues
def exportModelToSegmentationSpacing(model: vtkMRMLModelNode,
                                     spacingX: Annotated[float, Minimum(0), Default(0.1), Decimals(2), SingleStep(0.01)],
                                     spacingY: Annotated[float, Minimum(0), Default(0.1), Decimals(2), SingleStep(0.01)],
                                     spacingZ: Annotated[float, Minimum(0), Default(0.1), Decimals(2), SingleStep(0.01)],
                                     marginX: Annotated[float, Minimum(0), Default(1), Decimals(1), SingleStep(0.1)],
                                     marginY: Annotated[float, Minimum(0), Default(1), Decimals(1), SingleStep(0.1)],
                                     marginZ: Annotated[float, Minimum(0), Default(1), Decimals(1), SingleStep(0.1)]) -> SegmentationAndReferenceVolume:
    volumeMargin = [marginX, marginY, marginZ]
    volumeSpacing = [spacingX, spacingY, spacingZ]
    
    #create reference volume
    bounds = [0.]*6
    model.GetBounds(bounds)
    imageData = vtk.vtkImageData()
    imageSize = [int((bounds[axis * 2 + 1] - bounds[axis * 2] + volumeMargin[axis] * 2.0) / volumeSpacing[axis]) for axis in range(3)]
    imageOrigin = [ bounds[axis * 2] - volumeMargin[axis] for axis in range(3) ]
    imageData.SetDimensions(imageSize)
    imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
    imageData.GetPointData().GetScalars().Fill(0)
    referenceVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    referenceVolumeNode.SetName(f"{model.GetName()}_ReferenceVolume")
    referenceVolumeNode.SetOrigin(imageOrigin)
    referenceVolumeNode.SetSpacing(volumeSpacing)
    referenceVolumeNode.SetAndObserveImageData(imageData)
    referenceVolumeNode.CreateDefaultDisplayNodes()

    segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolumeNode)
    slicer.modules.segmentations.logic().ImportModelToSegmentationNode(model, segmentationNode)

    return SegmentationAndReferenceVolume(segmentationNode, referenceVolumeNode)

class _SomeClass:
    pass

def passThruScalarVolume(volume: vtkMRMLScalarVolumeNode) -> vtkMRMLScalarVolumeNode:
    # note: don't actually do this in a pipeline
    return volume

# simple items with implementation to test the logic's composition
def add(a: int, b: int) -> int:
    return a + b

def addFloat(a: float, b: float) -> float:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

def strlen(s: str) -> int:
    return len(s)

@parameterPack
class PlusMinus:
    positive: int
    negative: int

def plusMinus(a: int) -> PlusMinus:
    return PlusMinus(a, -a)

def makeTestMathPipeline(registeredPipelines):
    """
    See also: funcTestMathPipeline
    """
    pipeline = nx.DiGraph()

    # structure - None means overall input/output levels
    pipeline.add_node((0, None, "string"), datatype=str, position=0)
    pipeline.add_node((0, None, "additive"), datatype=int, position=1)
    pipeline.add_node((0, None, "factor"), datatype=int, position=2)

    pipeline.add_node((1, "strlen", "s"))
    pipeline.add_node((1, "strlen", "return"))

    pipeline.add_node((2, "add", "a"))
    pipeline.add_node((2, "add", "b"))
    pipeline.add_node((2, "add", "return"))

    pipeline.add_node((3, "multiply", "a"))
    pipeline.add_node((3, "multiply", "b"))
    pipeline.add_node((3, "multiply", "return"))

    pipeline.add_node((4, "add", "a"))
    pipeline.add_node((4, "add", "b"), fixed_value=1)
    pipeline.add_node((4, "add", "return"))

    pipeline.add_node((5, None, "value"), datatype=int)

    numNodes = len(pipeline.nodes)
    pipeline.add_edges_from([
        # connections into step 1
        ((0, None, "string"),       (1, "strlen", "s")),
        # connections into step 2
        ((1, "strlen", "return"),   (2, "add", "a")),
        ((0, None, "additive"),     (2, "add", "b")),
        # connections into step 3
        ((2, "add", "return"),      (3, "multiply", "a")),
        ((0, None, "factor"),       (3, "multiply", "b")),
        # connections into step 4
        ((3, "multiply", "return"), (4, "add", "a")),
        # final output
        ((4, "add", "return"),      (5, None, "value")),
    ])
    assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

    PipelineCreation.validation.validatePipeline(pipeline, registeredPipelines)

    return pipeline


def funcTestMathPipeline(string: str, additive: int, factor: int) -> int:
    """
    This gives the expected results from the pipeline from makeTestMathPipeline.
    """
    return ((len(string) + additive) * factor) + 1

class PipelineCreatorUtilTests(unittest.TestCase):
    def test_cleanType(self) -> None:
        from _PipelineCreator.PipelineCreation.CodeGeneration.util import typeAsCode
        self.assertEqual(typeAsCode(int), "int")
        self.assertEqual(typeAsCode(float), "float")
        self.assertEqual(typeAsCode(bool), "bool")
        self.assertEqual(typeAsCode(str), "str")
        self.assertEqual(typeAsCode(list[int]), "list[int]")
        self.assertEqual(typeAsCode(dict[str, int]), "dict[str, int]")
        self.assertEqual(typeAsCode(tuple[bool, float]), "tuple[bool, float]")
        self.assertEqual(typeAsCode(list[dict[tuple[str, int], list[bool]]]),
                         "list[dict[tuple[str, int], list[bool]]]")

        self.assertEqual(_SomeClass, eval(typeAsCode(_SomeClass)))


class PipelineCreatorRegistrationTest(unittest.TestCase):
    def setUp(self) -> None:
        slicer.mrmlScene.Clear()

    def test_pipeline_function_validation_successes(self):
        logic = PipelineCreatorLogic(False)

        def good1(iterations: int, doSomething: bool) -> float:
            pass
        logic.validatePipelineFunction(good1)
        del good1  # the del is to hopefully catch copy paste errors

        def good2(mesh: vtkMRMLModelNode, doSomething: bool) -> vtkMRMLModelNode:
            pass
        logic.validatePipelineFunction(good2)
        del good2

        def good3() -> vtkMRMLModelNode:
            pass
        logic.validatePipelineFunction(good3)
        del good3

        class StubClass:
            @staticmethod
            def goodStatic1() -> vtkMRMLModelNode:
                pass

            @staticmethod
            def goodStatic2(iterations: int, doSomething: bool) -> float:
                pass

        logic.validatePipelineFunction(StubClass.goodStatic1)
        logic.validatePipelineFunction(StubClass.goodStatic2)

    def test_pipeline_function_validation_return_type_errors(self):
        logic = PipelineCreatorLogic(False)

        def bad_unannotatedReturnType1():
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_unannotatedReturnType1)
        del bad_unannotatedReturnType1

        def bad_unannotatedReturnType2(mesh: vtkMRMLModelNode, doSomething: bool):
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_unannotatedReturnType2)
        del bad_unannotatedReturnType2

        def bad_noneReturnType1() -> None:
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_noneReturnType1)
        del bad_noneReturnType1

        def bad_noneReturnType2(mesh: vtkMRMLModelNode, doSomething: bool) -> None:
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_noneReturnType2)
        del bad_noneReturnType2

    def test_pipeline_function_validation_parameter_errors(self):
        logic = PipelineCreatorLogic(False)

        def bad_unannotatedParameter1(inputMesh) -> vtkMRMLModelNode:
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_unannotatedParameter1)
        del bad_unannotatedParameter1

        def bad_unannotatedParameter2(inputMesh: vtkMRMLModelNode, iterations) -> vtkMRMLModelNode:
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_unannotatedParameter2)
        del bad_unannotatedParameter2

        def bad_unannotatedParameter3(inputMesh, iterations: int) -> vtkMRMLModelNode:
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_unannotatedParameter3)
        del bad_unannotatedParameter3

        def bad_unannotatedParameter4(*args) -> vtkMRMLModelNode:
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_unannotatedParameter4)
        del bad_unannotatedParameter4

        def bad_unannotatedParameter5(**kwargs) -> vtkMRMLModelNode:
            pass
        with self.assertRaises(RuntimeError):
            logic.validatePipelineFunction(bad_unannotatedParameter5)
        del bad_unannotatedParameter5

    def test_duplicate_name(self):
        def func1(a: int) -> int:
            return 0
        def func2(a: int) -> int:
            return 0

        logic = PipelineCreatorLogic(False)
        logic.registerPipeline("func", func1, [])
        with self.assertRaises(RuntimeError):
            logic.registerPipeline("func", func2, [])


    def test_registration(self):
        logic = PipelineCreatorLogic(False)

        self.assertEqual(len(logic.registeredPipelines), 0)
        self.assertFalse(logic.isRegistered("subtraction"))
        self.assertFalse(logic.isRegistered("addition"))

        def subtraction(a: int, b: int) -> int:
            return a - b
        logic.registerPipeline("subtraction", subtraction, [])

        self.assertTrue(logic.isRegistered("subtraction"))
        self.assertEqual(len(logic.registeredPipelines), 1)
        self.assertEqual(logic.registeredPipelines["subtraction"].name, "subtraction")
        self.assertEqual(logic.registeredPipelines["subtraction"].parameters, {"a": int, "b": int})
        self.assertEqual(logic.registeredPipelines["subtraction"].returnType, int)
        self.assertEqual(logic.registeredPipelines["subtraction"].dependencies, [])

        def addition(c: int, d: int) -> int:
            return c + d
        logic.registerPipeline("addition", addition, [])

        self.assertTrue(logic.isRegistered("addition"))
        self.assertEqual(len(logic.registeredPipelines), 2)
        self.assertEqual(logic.registeredPipelines["addition"].name, "addition")
        self.assertEqual(logic.registeredPipelines["addition"].parameters, {"c": int, "d": int})
        self.assertEqual(logic.registeredPipelines["addition"].returnType, int)
        self.assertEqual(logic.registeredPipelines["addition"].dependencies, [])
        self.assertEqual(logic.registeredPipelines["subtraction"].name, "subtraction")
        self.assertEqual(logic.registeredPipelines["subtraction"].parameters, {"a": int, "b": int})
        self.assertEqual(logic.registeredPipelines["subtraction"].returnType, int)
        self.assertEqual(logic.registeredPipelines["subtraction"].dependencies, [])


class PipelineCreatorValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        slicer.mrmlScene.Clear()
        self.logic = PipelineCreatorLogic(False)
        self.logic.registerPipeline("passthru", passthru, [])
        self.logic.registerPipeline("centerOfX", centerOfX, [])
        self.logic.registerPipeline("decimation", decimation, [])
        self.logic.registerPipeline("translate", translate, [])
        self.logic.registerPipeline("passThruScalarVolume", passThruScalarVolume, [])

    def test_pipeline_validation_fail_if_empty(self):
        with self.assertRaises(ValueError):
            PipelineCreation.validation.validatePipeline(nx.DiGraph(), self.logic.registeredPipelines)

    def _makeDefaultTestPipeline(self, addEdges=True):
        pipeline = nx.DiGraph(name="Decimate then Translate")

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "mesh"), datatype=vtkMRMLModelNode, position=0)
        pipeline.add_node((0, None, "reduction"), datatype=float, position=1)
        pipeline.add_node((0, None, "translateX"), datatype=float, position=2)
        pipeline.add_node((0, None, "translateY"), datatype=float, position=3)

        pipeline.add_node((1, "decimation", "mesh"))
        pipeline.add_node((1, "decimation", "reduction"))
        pipeline.add_node((1, "decimation", "return"))

        pipeline.add_node((2, "translate", "mesh"))
        pipeline.add_node((2, "translate", "x"))
        pipeline.add_node((2, "translate", "y"))
        pipeline.add_node((2, "translate", "z"))
        pipeline.add_node((2, "translate", "return"))

        pipeline.add_node((3, None, "outputMesh"), datatype=vtkMRMLModelNode)

        # connectivity
        if addEdges:
            numNodes = len(pipeline.nodes)
            pipeline.add_edges_from([
                # connections into step 1
                ((0, None, "mesh"),           (1, "decimation", "mesh")),
                ((0, None, "reduction"),      (1, "decimation", "reduction")),
                # connections into step 2
                ((0, None, "translateX"),     (2, "translate", "x")),
                ((0, None, "translateY"),     (2, "translate", "y")),
                ((1, "decimation", "return"), (2, "translate", "mesh")),
                # final output
                ((2, "translate", "return"),  (3, None, "outputMesh"))
            ])
            assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

        # fixed values
        pipeline.nodes[(2, "translate", "z")]["fixed_value"] = 0
        return pipeline

    def test_pipeline_validation_standard_pass(self):
        pipeline = self._makeDefaultTestPipeline()
        PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

    def test_pipeline_validation_upcast(self):
        pipeline = nx.DiGraph()

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "labelmap"), datatype=vtkMRMLLabelMapVolumeNode, position=0)

        pipeline.add_node((1, "passThruScalarVolume", "volume"))
        pipeline.add_node((1, "passThruScalarVolume", "return"))

        pipeline.add_node((2, None, "scalarVolume"), datatype=vtkMRMLScalarVolumeNode, position=0)

        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "labelmap"),                 (1, "passThruScalarVolume", "volume")),
            # final output
            ((1, "passThruScalarVolume", "return"), (2, None, "scalarVolume"))
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

        PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

    def test_pipeline_validation_fail_no_datatype_on_step0(self):
        pipeline = self._makeDefaultTestPipeline()
        del pipeline.nodes[(0, None, "translateX")]["datatype"]
        with self.assertRaises(KeyError):
            PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

    def test_pipeline_validation_fail_nonfixed_unconnected_input(self):
        pipeline = self._makeDefaultTestPipeline()
        del pipeline.nodes[(2, "translate", "z")]["fixed_value"]
        with self.assertRaises(ValueError):
            PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

    def test_pipeline_validation_fail_mismatch_datatype_connection(self):
        pipeline = self._makeDefaultTestPipeline(addEdges=False)
        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "mesh"),       (1, "decimation", "mesh")),
            ((0, None, "reduction"),  (1, "decimation", "reduction")),
            # connections into step 2
            ((0, None, "translateX"), (2, "translate", "x")),
            ((0, None, "translateY"), (2, "translate", "y")),
            ((0, None, "translateX"), (2, "translate", "mesh")), # bad connection, float -> vtkMRMLModelNode
            # final output
            ((2, "translate", "return"),  (3, None, "outputMesh"))
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

        with self.assertRaises(TypeError):
            PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

    def test_pipeline_validation_fail_bad_fixed_value_type(self):
        pipeline = self._makeDefaultTestPipeline()
        pipeline.nodes[(2, "translate", "z")]["fixed_value"] = "This is not a number"
        with self.assertRaises(TypeError):
            PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

class PipelineCreatorCodeGenModuleTests(unittest.TestCase):
    def test_module(self):
        from _PipelineCreator.PipelineCreation.CodeGeneration.module import createModule
        code = createModule(
            name="TestPipeline",
            title="Test Pipeline",
            categories=["Examples", "Tests"],
            dependencies=["PipelineCreator"],
            contributors=["Connor Bowley"],
            helpText="This is a test",
            acknowledgementText="SlicerSALT is great",
            tab=" "*4)
        fullCode = "\n".join([code.imports, code.code])

        # just a class for the module to write to
        class ParentClass:
            def __init__(self):
                self.path = slicer.app.temporaryPath

        with TempPythonModule(fullCode) as tempPyModule:
            parent = ParentClass()
            module = tempPyModule.TestPipeline(parent)

            self.assertIsInstance(module, slicer.ScriptedLoadableModule.ScriptedLoadableModule)
            self.assertEqual(tempPyModule.TestPipeline.__name__, "TestPipeline")
            self.assertEqual(parent.title, "Test Pipeline")
            self.assertEqual(parent.categories, ["Examples", "Tests"])
            self.assertEqual(parent.dependencies, ["PipelineCreator"])
            self.assertEqual(parent.contributors, ["Connor Bowley"])
            self.assertEqual(parent.helpText, "This is a test")
            self.assertEqual(parent.acknowledgementText, "SlicerSALT is great")

class PipelineCreatorCodeGenLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        slicer.mrmlScene.Clear()
        self.logic = PipelineCreatorLogic(False)
        # node pipelines
        self.logic.registerPipeline("passthru", passthru, [])
        self.logic.registerPipeline("centerOfX", centerOfX, [])
        self.logic.registerPipeline("decimation", decimation, [])
        self.logic.registerPipeline("translate", translate, [])
        # math pipelines
        self.logic.registerPipeline("add", add, [])
        self.logic.registerPipeline("multiply", multiply, [])
        self.logic.registerPipeline("plusMinus", plusMinus, [])
        self.logic.registerPipeline("strlen", strlen, [])

    def test_logic(self):
        pipeline = makeTestMathPipeline(self.logic.registeredPipelines)

        from _PipelineCreator.PipelineCreation.CodeGeneration.logic import createLogic
        code = createLogic("TestPipelineLogic", pipeline, self.logic.registeredPipelines, "", tab=" "*4)
        fullCode = "\n".join([code.imports, code.code])

        with TempPythonModule(fullCode) as tempModule:
            logic = tempModule.TestPipelineLogic()
            self.assertIsInstance(logic, slicer.ScriptedLoadableModule.ScriptedLoadableModuleLogic)
            self.assertEqual(tempModule.TestPipelineLogic.__name__, "TestPipelineLogic")
            self.assertEqual(logic.run("hi", 2, 3), funcTestMathPipeline("hi", 2, 3))
            self.assertEqual(logic.run("hello", 12, -3), funcTestMathPipeline("hello", 12, -3))
            self.assertEqual(logic.run("", 0, 0), funcTestMathPipeline("", 0, 0))

    def test_multiple_overall_outputs(self):
        pipeline = nx.DiGraph()

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "a"), datatype=int, position=0)
        pipeline.add_node((0, None, "b"), datatype=int, position=1)

        pipeline.add_node((1, "add", "a"))
        pipeline.add_node((1, "add", "b"))
        pipeline.add_node((1, "add", "return"))

        pipeline.add_node((2, "multiply", "a"))
        pipeline.add_node((2, "multiply", "b"))
        pipeline.add_node((2, "multiply", "return"))

        pipeline.add_node((3, None, "summation"), datatype=int, position=0)
        pipeline.add_node((3, None, "multiplication"), datatype=int, position=1)

        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "a"), (1, "add", "a")),
            ((0, None, "b"), (1, "add", "b")),
            # connections into step 2
            ((0, None, "a"), (2, "multiply", "a")),
            ((0, None, "b"), (2, "multiply", "b")),
            # final output
            ((1, "add", "return"), (3, None, "summation")),
            ((2, "multiply", "return"), (3, None, "multiplication")),
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"
        PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

        from _PipelineCreator.PipelineCreation.CodeGeneration import createLogic, createParameterNode
        paramNodeCode = createParameterNode("TestPipeline", pipeline, tab=" "*4)
        logicCode = createLogic("TestPipelineLogic", pipeline, self.logic.registeredPipelines, "TestPipelineOutputs", tab=" "*4)
        fullCode = "\n".join([paramNodeCode.imports, logicCode.imports, paramNodeCode.code, logicCode.code])

        with TempPythonModule(fullCode) as tempModule:
            logic = tempModule.TestPipelineLogic()
            self.assertIsInstance(logic, slicer.ScriptedLoadableModule.ScriptedLoadableModuleLogic)
            self.assertEqual(tempModule.TestPipelineLogic.__name__, "TestPipelineLogic")
            self.assertEqual(logic.run(1, 1), tempModule.TestPipelineOutputs(2, 1))
            self.assertEqual(logic.run(2, 2), tempModule.TestPipelineOutputs(4, 4))
            self.assertEqual(logic.run(3, 4), tempModule.TestPipelineOutputs(7, 12))

    def test_parameter_pack_intermediate_output(self):
        pipeline = nx.DiGraph()

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "a"), datatype=int, position=0)

        pipeline.add_node((1, "plusMinus", "a"))
        pipeline.add_node((1, "plusMinus", "return"))
        pipeline.add_node((1, "plusMinus", "return.positive"))
        pipeline.add_node((1, "plusMinus", "return.negative"))

        pipeline.add_node((2, "multiply", "a"))
        pipeline.add_node((2, "multiply", "b"))
        pipeline.add_node((2, "multiply", "return"))

        pipeline.add_node((3, None, "pos"), datatype=int, position=0)
        pipeline.add_node((3, None, "neg"), datatype=int, position=1)
        pipeline.add_node((3, None, "multiplication"), datatype=int, position=2)

        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "a"), (1, "plusMinus", "a")),
            # connections into step 2
            ((1, "plusMinus", "return.positive"), (2, "multiply", "a")),
            ((1, "plusMinus", "return.negative"), (2, "multiply", "b")),
            # final output
            ((1, "plusMinus", "return.positive"), (3, None, "pos")),
            ((1, "plusMinus", "return.negative"), (3, None, "neg")),
            ((2, "multiply", "return"), (3, None, "multiplication")),
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"
        PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

        from _PipelineCreator.PipelineCreation.CodeGeneration import createLogic, createParameterNode
        paramNodeCode = createParameterNode("TestPipeline", pipeline, tab=" "*4)
        logicCode = createLogic("TestPipelineLogic", pipeline, self.logic.registeredPipelines, "TestPipelineOutputs", tab=" "*4)
        fullCode = "\n".join([paramNodeCode.imports, logicCode.imports, paramNodeCode.code, logicCode.code])

        with TempPythonModule(fullCode) as tempModule:
            logic = tempModule.TestPipelineLogic()
            self.assertIsInstance(logic, slicer.ScriptedLoadableModule.ScriptedLoadableModuleLogic)
            self.assertEqual(tempModule.TestPipelineLogic.__name__, "TestPipelineLogic")
            self.assertEqual(logic.run(1), tempModule.TestPipelineOutputs(1, -1, -1))
            self.assertEqual(logic.run(-2), tempModule.TestPipelineOutputs(-2, 2, -4))
            self.assertEqual(logic.run(3), tempModule.TestPipelineOutputs(3, -3, -9))

    def test_delete_intermediate_nodes(self):
        # structure - None means overall input/output levels
        pipeline = nx.DiGraph()
        pipeline.add_node((0, None, "mesh"), datatype=vtkMRMLModelNode)

        pipeline.add_node((1, "decimation", "mesh"))
        pipeline.add_node((1, "decimation", "reduction"), fixed_value=0.5)  # set fixed_value inline
        pipeline.add_node((1, "decimation", "return"))

        pipeline.add_node((2, "translate", "mesh"))
        pipeline.add_node((2, "translate", "x"), fixed_value=0)
        pipeline.add_node((2, "translate", "y"), fixed_value=0)
        pipeline.add_node((2, "translate", "z"), fixed_value=0)
        pipeline.add_node((2, "translate", "return"))

        pipeline.add_node((3, None, "outputMesh"), datatype=vtkMRMLModelNode)

        # connectivity
        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "mesh"),           (1, "decimation", "mesh")),
            # connections into step 2
            ((1, "decimation", "return"), (2, "translate", "mesh")),
            # final output
            ((2, "translate", "return"),  (3, None, "outputMesh"))
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"
        PipelineCreation.validation.validatePipeline(pipeline, self.logic.registeredPipelines)

        from _PipelineCreator.PipelineCreation.CodeGeneration.logic import createLogic
        code = createLogic("TestPipelineLogicDeleteIntermediates", pipeline, self.logic.registeredPipelines, "", tab=" "*4)
        fullCode = "\n".join([code.imports, code.code])

        with TempPythonModule(fullCode) as tempModule:
            logic = tempModule.TestPipelineLogicDeleteIntermediates()

            model = makeSphereModel(self)
            numModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
            _ = logic.run(model, delete_intermediate_nodes=False)
            # make sure there is an intermediate results still remaining for each step
            newNumModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
            self.assertEqual(newNumModels - numModels, 2)


class PipelineCreatorFullTests(unittest.TestCase):
    def setUp(self) -> None:
        slicer.mrmlScene.Clear()
        self.logic = PipelineCreatorLogic(False)
        # node pipelines
        self.logic.registerPipeline("passthru", passthru, [])
        self.logic.registerPipeline("centerOfX", centerOfX, [])
        self.logic.registerPipeline("decimation", decimation, [])
        self.logic.registerPipeline("translate", translate, [])
        self.logic.registerPipeline("exportModelToSegmentationSpacing", exportModelToSegmentationSpacing, [])
        # math pipelines
        self.logic.registerPipeline("add", add, [])
        self.logic.registerPipeline("addFloat", addFloat, [])
        self.logic.registerPipeline("multiply", multiply, [])
        self.logic.registerPipeline("strlen", strlen, [])

    def _test_the_whole_shebang_widget_paramnode_connections(self, widget):
        param = widget._parameterNode
        model1 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        model2 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")

        meshWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.mesh")
        reductionWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.reduction")
        translateXWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.translateX")
        translateYWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.translateY")

        self.assertIsNone(meshWidget.currentNode())
        self.assertEqual(reductionWidget.value, 0.0)
        self.assertEqual(translateXWidget.value, 0.0)
        self.assertEqual(translateYWidget.value, 0.0)
        self.assertIsNone(param.inputs.mesh)
        self.assertEqual(param.inputs.reduction, 0.0)
        self.assertEqual(param.inputs.translateX, 0.0)
        self.assertEqual(param.inputs.translateY, 0.0)

        # update gui
        meshWidget.setCurrentNode(model2)
        reductionWidget.value = 7.3
        translateXWidget.value = 17.3
        translateYWidget.value = -27.3
        self.assertIs(meshWidget.currentNode(), model2)
        self.assertEqual(reductionWidget.value, 7.3)
        self.assertEqual(translateXWidget.value, 17.3)
        self.assertEqual(translateYWidget.value, -27.3)
        self.assertIs(param.inputs.mesh, model2)
        self.assertEqual(param.inputs.reduction, 7.3)
        self.assertEqual(param.inputs.translateX, 17.3)
        self.assertEqual(param.inputs.translateY, -27.3)

        # update parameterNode
        param.inputs.mesh = model1
        param.inputs.reduction = 0.5
        param.inputs.translateX = 1
        param.inputs.translateY = -2
        self.assertIs(meshWidget.currentNode(), model1)
        self.assertEqual(reductionWidget.value, 0.5)
        self.assertEqual(translateXWidget.value, 1)
        self.assertEqual(translateYWidget.value, -2)
        self.assertIs(param.inputs.mesh, model1)
        self.assertEqual(param.inputs.reduction, 0.5)
        self.assertEqual(param.inputs.translateX, 1)
        self.assertEqual(param.inputs.translateY, -2)

    def _test_the_whole_shebang_logic_run(self, logic, widget):
        model = makeSphereModel(self)

        # test logic with positional arguments
        def testLogicPositionalArgs():
            numModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
            pipelinedModel = logic.run(model, 0.5, 1, -1)
            self.assertEqual(pipelinedModel.GetMesh().GetCenter(), (1.0, -1.0, 0.0))
            # decimate is a target reduction, not a guarantee, so use a forgiving check
            self.assertLess(pipelinedModel.GetMesh().GetNumberOfCells(), model.GetMesh().GetNumberOfCells())
            # make sure there are no intermediate results hanging
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode"), numModels + 1)
        testLogicPositionalArgs()

        # test logic with keyword arguments
        def testLogicKeywordArgs():
            numModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
            pipelinedModel2 = logic.run(model, reduction=0.5, translateX=-10, translateY=33)
            self.assertEqual(pipelinedModel2.GetMesh().GetCenter(), (-10.0, 33.0, 0.0))
            # decimate is a target reduction, not a guarantee, so use a forgiving check
            self.assertLess(pipelinedModel2.GetMesh().GetNumberOfCells(), model.GetMesh().GetNumberOfCells())
            # make sure there are no intermediate results hanging
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode"), numModels + 1)
        testLogicKeywordArgs()

        # test the widget
        def testWidget():
            outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
            numModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")

            meshWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.mesh")
            reductionWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.reduction")
            translateXWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.translateX")
            translateYWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.translateY")
            outputWidget = findChildWidgetForParameter(widget.paramWidget, "outputs.outputMesh")

            meshWidget.setCurrentNode(model)
            reductionWidget.value = 0.5
            translateXWidget.value = 100
            translateYWidget.value = -33.3

            outputWidget.setCurrentNode(outputModel)

            widget.runButton.click()

            self.assertAlmostEqual(outputModel.GetMesh().GetCenter()[0], 100, 5)
            self.assertAlmostEqual(outputModel.GetMesh().GetCenter()[1], -33.3, 5)
            self.assertAlmostEqual(outputModel.GetMesh().GetCenter()[2], 0, 5)
            # decimate is a target reduction, not a guarantee, so use a forgiving check
            self.assertLess(outputModel.GetMesh().GetNumberOfCells(), model.GetMesh().GetNumberOfCells())

             # make sure there are no intermediate results hanging.
             # note: we gave an output node so there should be _no_ new nodes
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode"), numModels)
        testWidget()

    def test_the_whole_shebang(self):
        slicer.mrmlScene.Clear()

        pipeline = nx.DiGraph(name="Decimate then Translate")

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "mesh"), datatype=vtkMRMLModelNode)
        pipeline.add_node((0, None, "reduction"), datatype=float)
        pipeline.add_node((0, None, "translateX"), datatype=float)
        pipeline.add_node((0, None, "translateY"), datatype=float)

        pipeline.add_node((1, "decimation", "mesh"))
        pipeline.add_node((1, "decimation", "reduction"))
        pipeline.add_node((1, "decimation", "return"))

        pipeline.add_node((2, "translate", "mesh"))
        pipeline.add_node((2, "translate", "x"))
        pipeline.add_node((2, "translate", "y"))
        pipeline.add_node((2, "translate", "z"))
        pipeline.add_node((2, "translate", "return"))

        pipeline.add_node((3, None, "outputMesh"), datatype=vtkMRMLModelNode)

        # connectivity
        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "mesh"),           (1, "decimation", "mesh")),
            ((0, None, "reduction"),      (1, "decimation", "reduction")),
            # connections into step 2
            ((0, None, "translateX"),     (2, "translate", "x")),
            ((0, None, "translateY"),     (2, "translate", "y")),
            ((1, "decimation", "return"), (2, "translate", "mesh")),
            # final output
            ((2, "translate", "return"),  (3, None, "outputMesh"))
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

        # fixed values
        pipeline.nodes[(2, "translate", "z")]["fixed_value"] = 0

        moduleName = "PipelineCreatorTestModule"

        with tempfile.TemporaryDirectory() as tempDir:
            # Make output
            self.logic.createPipeline(
                name=moduleName,
                outputDirectory=tempDir,
                pipeline=pipeline,
            )

            # test loading the new slicer module
            factory = slicer.app.moduleManager().factoryManager()
            factory.registerModule(qt.QFileInfo(os.path.join(tempDir, moduleName + ".py")))
            factory.loadModules([moduleName])

            slicer.util.selectModule(moduleName)

            widget = slicer.modules.PipelineCreatorTestModuleWidget
            logic = widget.logic
            self.assertEqual(logic.__class__.__name__, "PipelineCreatorTestModuleLogic")

            self._test_the_whole_shebang_widget_paramnode_connections(widget)
            self._test_the_whole_shebang_logic_run(logic, widget)
            # import pdb; pdb.set_trace()

    def test_the_whole_shebang_no_models(self):
        pipeline = makeTestMathPipeline(self.logic.registeredPipelines)

        moduleName = "PipelineCreatorTestMathModule"

        with tempfile.TemporaryDirectory() as tempDir:
            # Make output
            self.logic.createPipeline(
                name=moduleName,
                outputDirectory=tempDir,
                pipeline=pipeline,
            )

            # test loading the new slicer module
            factory = slicer.app.moduleManager().factoryManager()
            factory.registerModule(qt.QFileInfo(os.path.join(tempDir, moduleName + ".py")))
            factory.loadModules([moduleName])

            slicer.util.selectModule(moduleName)

            widget = slicer.modules.PipelineCreatorTestMathModuleWidget
            logic = widget.logic

            numNodes = slicer.mrmlScene.GetNumberOfNodes()

            # test logic run
            self.assertEqual(logic.__class__.__name__, "PipelineCreatorTestMathModuleLogic")
            self.assertEqual(logic.run("hi", 2, 3), funcTestMathPipeline("hi", 2, 3))
            self.assertEqual(logic.run("hello", 12, -3), funcTestMathPipeline("hello", 12, -3))
            self.assertEqual(logic.run("", 0, 0), funcTestMathPipeline("", 0, 0))

            # test widget run
            stringWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.string")
            additiveWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.additive")
            factorWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.factor")
            outputWidget = findChildWidgetForParameter(widget.paramWidget, "outputs.value")

            stringWidget.text = "somestring"
            additiveWidget.value = -4
            factorWidget.value = 33

            widget.runButton.click()

            expectedValue = funcTestMathPipeline("somestring", -4, 33)
            self.assertEqual(widget._parameterNode.outputs.value, expectedValue)
            self.assertEqual(outputWidget.text, str(expectedValue))

            self.assertEqual(slicer.mrmlScene.GetNumberOfNodes(), numNodes)
            # import pdb; pdb.set_trace()

    def test_the_whole_shebang_multiple_output(self):
        slicer.mrmlScene.Clear()

        pipeline = nx.DiGraph(name="Multi output")

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "mesh"), datatype=vtkMRMLModelNode, position=0)
        pipeline.add_node((0, None, "reduction"), datatype=float, position=1)
        pipeline.add_node((0, None, "translateX"), datatype=float, position=2)
        pipeline.add_node((0, None, "translateY"), datatype=float, position=3)

        pipeline.add_node((1, "decimation", "mesh"))
        pipeline.add_node((1, "decimation", "reduction"))
        pipeline.add_node((1, "decimation", "return"))

        pipeline.add_node((2, "translate", "mesh"))
        pipeline.add_node((2, "translate", "x"))
        pipeline.add_node((2, "translate", "y"))
        pipeline.add_node((2, "translate", "z"))
        pipeline.add_node((2, "translate", "return"))

        pipeline.add_node((3, "addFloat", "a"))
        pipeline.add_node((3, "addFloat", "b"))
        pipeline.add_node((3, "addFloat", "return"))

        pipeline.add_node((4, None, "mesh"), datatype=vtkMRMLModelNode, position=0)
        pipeline.add_node((4, None, "xyTranslationSum"), datatype=float, position=1)

        # connectivity
        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "mesh"),           (1, "decimation", "mesh")),
            ((0, None, "reduction"),      (1, "decimation", "reduction")),
            # connections into step 2
            ((0, None, "translateX"),     (2, "translate", "x")),
            ((0, None, "translateY"),     (2, "translate", "y")),
            ((1, "decimation", "return"), (2, "translate", "mesh")),
            # connections into step 3
            ((0, None, "translateX"),     (3, "addFloat", "a")),
            ((0, None, "translateY"),     (3, "addFloat", "b")),
            # final output
            ((2, "translate", "return"),  (4, None, "mesh")),
            ((3, "addFloat", "return"),   (4, None, "xyTranslationSum")),
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

        # fixed values
        pipeline.nodes[(2, "translate", "z")]["fixed_value"] = 0

        moduleName = "PipelineCreatorTestModuleMultiOutput"

        with tempfile.TemporaryDirectory() as tempDir:
            # Make output
            self.logic.createPipeline(
                name=moduleName,
                outputDirectory=tempDir,
                pipeline=pipeline,
            )

            # test loading the new slicer module
            factory = slicer.app.moduleManager().factoryManager()
            factory.registerModule(qt.QFileInfo(os.path.join(tempDir, moduleName + ".py")))
            factory.loadModules([moduleName])

            slicer.util.selectModule(moduleName)

            widget = slicer.modules.PipelineCreatorTestModuleMultiOutputWidget

            model = makeSphereModel(self)
            outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
            numModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")

            meshWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.mesh")
            reductionWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.reduction")
            translateXWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.translateX")
            translateYWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.translateY")
            outputMeshWidget = findChildWidgetForParameter(widget.paramWidget, "outputs.mesh")
            outputXYSumWidget = findChildWidgetForParameter(widget.paramWidget, "outputs.xyTranslationSum")

            meshWidget.setCurrentNode(model)
            reductionWidget.value = 0.5
            translateXWidget.value = 100
            translateYWidget.value = -33.3

            outputMeshWidget.setCurrentNode(outputModel)

            widget.runButton.click()

            self.assertAlmostEqual(outputModel.GetMesh().GetCenter()[0], 100, 5)
            self.assertAlmostEqual(outputModel.GetMesh().GetCenter()[1], -33.3, 5)
            self.assertAlmostEqual(outputModel.GetMesh().GetCenter()[2], 0, 5)
            # decimate is a target reduction, not a guarantee, so use a forgiving check
            self.assertLess(outputModel.GetMesh().GetNumberOfCells(), model.GetMesh().GetNumberOfCells())

            self.assertAlmostEqual(outputXYSumWidget.value, 66.7, 5)

            # make sure there are no intermediate results hanging.
            # note: we gave an output node so there should be _no_ new nodes
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode"), numModels)


    def test_the_whole_shebang_single_parameterPack_output(self):
        slicer.mrmlScene.Clear()

        pipeline = nx.DiGraph(name="Multi output")

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "mesh"), datatype=vtkMRMLModelNode, position=0)

        pipeline.add_node((1, "exportModelToSegmentationSpacing", "model"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "spacingX"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "spacingY"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "spacingZ"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "marginX"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "marginY"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "marginZ"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "return"))

        pipeline.add_node((2, None, "segAndVol"), datatype=SegmentationAndReferenceVolume)

        # connectivity
        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "mesh"),           (1, "exportModelToSegmentationSpacing", "model")),
            # final output
            ((1, "exportModelToSegmentationSpacing", "return"),  (2, None, "segAndVol")),
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

        # fixed values
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "spacingX")]["fixed_value"] = 0.1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "spacingY")]["fixed_value"] = 0.1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "spacingZ")]["fixed_value"] = 0.1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "marginX")]["fixed_value"] = 1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "marginY")]["fixed_value"] = 1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "marginZ")]["fixed_value"] = 1

        moduleName = "PipelineCreatorTestModuleParameterPackOutput"

        with tempfile.TemporaryDirectory() as tempDir:
            # Make output
            self.logic.createPipeline(
                name=moduleName,
                outputDirectory=tempDir,
                pipeline=pipeline,
            )

            # test loading the new slicer module
            factory = slicer.app.moduleManager().factoryManager()
            factory.registerModule(qt.QFileInfo(os.path.join(tempDir, moduleName + ".py")))
            factory.loadModules([moduleName])

            slicer.util.selectModule(moduleName)

            widget = slicer.modules.PipelineCreatorTestModuleParameterPackOutputWidget

            model = makeSphereModel(self)
            outputSeg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
            outputVol = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")

            numModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
            numSegs = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLSegmentationNode")
            numVols = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLScalarVolumeNode")

            meshWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.mesh")
            outputSegWidget = findChildWidgetForParameter(widget.paramWidget, "outputs.segAndVol.segmentation")
            outputVolWidget = findChildWidgetForParameter(widget.paramWidget, "outputs.segAndVol.referenceVolume")

            meshWidget.setCurrentNode(model)
            outputSegWidget.setCurrentNode(outputSeg)
            outputVolWidget.setCurrentNode(outputVol)

            widget.runButton.click()

            self.assertEqual(outputSeg.GetSegmentation().GetNumberOfSegments(), 1)
            # TODO: Enable this line once reference propagation is fixed
            # self.assertEqual(outputSeg.GetNodeReference(outputSeg.GetReferenceImageGeometryReferenceRole()), outputVol)

            # make sure there are no intermediate results hanging.
            # note: we gave an output node so there should be _no_ new nodes
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode"), numModels)
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLSegmentationNode"), numSegs)
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLScalarVolumeNode"), numVols)

    def test_the_whole_shebang_keep_referenced_nodes(self):
        slicer.mrmlScene.Clear()

        pipeline = nx.DiGraph(name="Multi output")

        # structure - None means overall input/output levels
        pipeline.add_node((0, None, "mesh"), datatype=vtkMRMLModelNode, position=0)

        pipeline.add_node((1, "exportModelToSegmentationSpacing", "model"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "spacingX"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "spacingY"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "spacingZ"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "marginX"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "marginY"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "marginZ"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "return"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "return.segmentation"))
        pipeline.add_node((1, "exportModelToSegmentationSpacing", "return.referenceVolume"))

        pipeline.add_node((2, None, "segmentation"), datatype=vtkMRMLSegmentationNode)

        # connectivity
        numNodes = len(pipeline.nodes)
        pipeline.add_edges_from([
            # connections into step 1
            ((0, None, "mesh"),           (1, "exportModelToSegmentationSpacing", "model")),
            # final output
            ((1, "exportModelToSegmentationSpacing", "return.segmentation"),  (2, None, "segmentation")),
        ])
        assert len(pipeline.nodes) == numNodes, "did not want to add new nodes"

        # fixed values
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "spacingX")]["fixed_value"] = 0.1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "spacingY")]["fixed_value"] = 0.1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "spacingZ")]["fixed_value"] = 0.1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "marginX")]["fixed_value"] = 1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "marginY")]["fixed_value"] = 1
        pipeline.nodes[(1, "exportModelToSegmentationSpacing", "marginZ")]["fixed_value"] = 1

        moduleName = "PipelineCreatorTestModuleKeepReferencedNodes"

        with tempfile.TemporaryDirectory() as tempDir:
            # Make output
            self.logic.createPipeline(
                name=moduleName,
                outputDirectory=tempDir,
                pipeline=pipeline,
            )

            with open(os.path.join(tempDir, f"{moduleName}.py")) as f:
                print(f.read())

            # test loading the new slicer module
            factory = slicer.app.moduleManager().factoryManager()
            factory.registerModule(qt.QFileInfo(os.path.join(tempDir, moduleName + ".py")))
            factory.loadModules([moduleName])

            slicer.util.selectModule(moduleName)

            widget = slicer.modules.PipelineCreatorTestModuleKeepReferencedNodesWidget

            model = makeSphereModel(self)
            outputSeg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")

            numModels = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode")
            numSegs = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLSegmentationNode")
            numVols = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLScalarVolumeNode")

            meshWidget = findChildWidgetForParameter(widget.paramWidget, "inputs.mesh")
            outputSegWidget = findChildWidgetForParameter(widget.paramWidget, "outputs.segmentation")

            meshWidget.setCurrentNode(model)
            outputSegWidget.setCurrentNode(outputSeg)

            widget.runButton.click()

            self.assertEqual(outputSeg.GetSegmentation().GetNumberOfSegments(), 1)

            self.assertIsNotNone(outputSeg.GetNodeReference(outputSeg.GetReferenceImageGeometryReferenceRole()))

            # make sure there are no intermediate results hanging.
            # note: we gave an output node so there should be _no_ new nodes
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelNode"), numModels)
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLSegmentationNode"), numSegs)
            # should have 1 more volume than before
            self.assertEqual(slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLScalarVolumeNode"), numVols + 1)
