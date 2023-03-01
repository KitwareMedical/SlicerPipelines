import importlib
import os
import pickle  # this shows as unused but is used by test_cleanType during the eval
import tempfile
from typing import Annotated
import unittest

import networkx as nx

import qt

import slicer
import vtk

from slicer.parameterNodeWrapper import (
    findChildWidgetForParameter,
    WithinRange,
)

from MRMLCorePython import (
    vtkMRMLModelNode,
)

from PipelineCreator import PipelineCreatorWidget, PipelineCreatorLogic
from _PipelineCreator import PipelineCreation


# note: creates _Python_ module not _slicer_ module
def createTempPythonModule(codeAsString):
    # load the generated code into a temporary module
    # https://stackoverflow.com/a/60054279
    spec = importlib.util.spec_from_loader('tempModule', loader=None)
    tempModule = importlib.util.module_from_spec(spec)
    exec(codeAsString, tempModule.__dict__)
    return tempModule

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

class _SomeClass:
    pass


# simple items with implementation to test the logic's composition
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

def strlen(s: str) -> int:
    return len(s)

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

        tempPyModule = createTempPythonModule(fullCode)
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
        self.logic.registerPipeline("strlen", strlen, [])

    def test_logic(self):
        pipeline = makeTestMathPipeline(self.logic.registeredPipelines)

        from _PipelineCreator.PipelineCreation.CodeGeneration.logic import createLogic
        code = createLogic("TestPipelineLogic", pipeline, self.logic.registeredPipelines, tab=" "*4)
        fullCode = "\n".join([code.imports, code.code])

        tempModule = createTempPythonModule(fullCode)
        logic = tempModule.TestPipelineLogic()
        self.assertIsInstance(logic, slicer.ScriptedLoadableModule.ScriptedLoadableModuleLogic)
        self.assertEqual(tempModule.TestPipelineLogic.__name__, "TestPipelineLogic")
        self.assertEqual(logic.run("hi", 2, 3), funcTestMathPipeline("hi", 2, 3))
        self.assertEqual(logic.run("hello", 12, -3), funcTestMathPipeline("hello", 12, -3))
        self.assertEqual(logic.run("", 0, 0), funcTestMathPipeline("", 0, 0))

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
        code = createLogic("TestPipelineLogicDeleteIntermediates", pipeline, self.logic.registeredPipelines, tab=" "*4)
        fullCode = "\n".join([code.imports, code.code])

        tempModule = createTempPythonModule(fullCode)
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
        # math pipelines
        self.logic.registerPipeline("add", add, [])
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
        self.logic = PipelineCreatorLogic(False)
        self.logic.registerPipeline("passthru", passthru, [])
        self.logic.registerPipeline("centerOfX", centerOfX, [])
        self.logic.registerPipeline("decimation", decimation, [])
        self.logic.registerPipeline("translate", translate, [])

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
