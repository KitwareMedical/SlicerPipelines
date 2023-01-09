import networkx as nx
import pickle
import re
import textwrap

from MRMLCorePython import vtkMRMLNode

from slicer.parameterNodeWrapper import unannotatedType

from _PipelineCreatorMk2.PipelineRegistrar import PipelineInfo

from _PipelineCreatorMk2.PipelineCreation.util import (
    getStep,
    groupNodesByStep,
    splitParametersFromReturn,
)
from _PipelineCreatorMk2.PipelineCreation.CodeGeneration.util import (
    CodePiece,
    cleanupImports,
    importCodeForType,
    importCodeForTypes,
    typeAsCode,
    valueAsCode,
)

__all__ = ["createLogic"]


def _getReturnType(lastStepNodes, fullPipeline):
    assert len(lastStepNodes) != 0
    if len(lastStepNodes) == 1:
        return fullPipeline.nodes[lastStepNodes[0]]['datatype']
    else:
        raise NotImplementedError("Need to implement multiple return type")


def _makeToplevelFunctionSignature(functionName, fullPipeline, returnType) -> str:
    returnTypeCode = typeAsCode(returnType)
    params, _ = getStep(0, fullPipeline)
    parameterString = ", ".join(f"{param[2]}: {typeAsCode(fullPipeline.nodes[param]['datatype'])}"
                                for param in params)
    necessaryImports = importCodeForType(returnType) + "\n" + importCodeForTypes(params, fullPipeline)
    return f"{functionName}({parameterString}, *, delete_intermediate_nodes=True) -> {returnTypeCode}", necessaryImports


def _varName(node) -> str:
    step = node[0]
    if step == 0:
        # function signature gets nicer names
        return node[2]  # paramName
    else:
        # step_{step#}_{pipelineName}_{paramName}
        # e.g. step_1_cleanPolyData_return
        # (dots are replaced with underscores, only applicable for "return.subitem")
        cleanedPipelineName = _cleanPipelineName(node=node)
        return f"step_{node[0]}_{cleanedPipelineName}_{node[2].replace('.', '_')}"


def _cleanPipelineName(step=None, node=None):
    if step is not None:
        name = step[0][1]
    elif node is not None:
        name = node[1]
    else:
        raise RuntimeError("BUG: step and node can't both be None.")

    return re.sub('\W|^(?=\d)','_', name)


def _stepFunctionName(step) -> str:
    stepNum = step[0][0]
    cleanedPipelineName = _cleanPipelineName(step)
    return f"function_{stepNum}_{cleanedPipelineName}"


def _stepFunctionValue(step, registeredPipelines):
    pipelineName = step[0][1]
    info = registeredPipelines[pipelineName]
    return f"pickle.loads({pickle.dumps(info.function)})"


def _returnVarNames(returns) -> list[str]:
    return [_varName(r) for r in returns]


def _getInput(node, pipeline: nx.DiGraph) -> str:
    """
    Assumes there will be exactly one inbound connection or a fixed value. This should be validated
    by the code in validation.py
    """
    if "fixed_value" in pipeline.nodes[node]:
        return valueAsCode(pipeline.nodes[node]["fixed_value"])
    else:
        # first [0] assumes there is exactly 1 inbound connection.
        # second [0] is because the tuple is (fromNode, toNode) and node is the toNode
        return _varName(list(pipeline.in_edges(node))[0][0])


def _generateStepCode(step, pipeline: nx.DiGraph, registeredPipelines: dict[str, PipelineInfo], tab: str) -> str:
    """
    Each output node is given a well known variable name by the 
    """
    parameters, returns = splitParametersFromReturn(step)
    stepArguments = [
        f"{node[2]}={_getInput(node, pipeline)}" for node in parameters
    ]
    stepArgumentsCode = textwrap.indent(",\n".join(stepArguments), tab)

    returnVariables = _returnVarNames(returns)

    stepFunctionName = _stepFunctionName(step)
    stepFunctionValue = _stepFunctionValue(step, registeredPipelines)

    stepCode = f"""# step {step[0][0]} - {step[0][1]}
{stepFunctionName} = {stepFunctionValue}
{", ".join(returnVariables)} = {stepFunctionName}(
{stepArgumentsCode})
"""
    return stepCode


def _getReturnedVariables(lastStep, pipeline: nx.DiGraph):
    return [_getInput(n, pipeline) for n in lastStep]


def _generateReturnStatement(lastStep, pipeline: nx.DiGraph) -> str:
    return "return " + ", ".join(_getReturnedVariables(lastStep, pipeline))


def _getNamesOfMRMLNodeIntermediates(pipeline: nx.DiGraph):
    steps = groupNodesByStep(pipeline)
    mrmlReturnNames = []
    for step in steps:
        _, returns = splitParametersFromReturn(step)
        mrmlReturns = [ret for ret in returns if issubclass(unannotatedType(pipeline.nodes[ret]["datatype"]), vtkMRMLNode)]
        mrmlReturnNames += _returnVarNames(mrmlReturns)

    # remove returned variables, so we only have intermediates
    returnVars = _getReturnedVariables(steps[-1], pipeline)
    return [m for m in mrmlReturnNames if m not in returnVars]


def _generateRunFunction(pipeline: nx.DiGraph,
                         registeredPipelines: dict[str, PipelineInfo],
                         runFunctionName: str,
                         tab: str) -> tuple[str, str]:
    """
    Returns (function-code, necessary-imports)
    """
    steps = groupNodesByStep(pipeline)
    returnType = _getReturnType(steps[-1], pipeline)
    functionSignature, necessaryImports = _makeToplevelFunctionSignature(runFunctionName, pipeline, returnType)
    body = "\n".join(_generateStepCode(step, pipeline, registeredPipelines, tab) for step in steps[1:-1])
    returnStatement = _generateReturnStatement(steps[-1], pipeline)

    intermediateMRMLNodes = _getNamesOfMRMLNodeIntermediates(pipeline)
    intermediateMRMLNodesDeclaration = "\n".join(f"{name} = None" for name in intermediateMRMLNodes)
    intermediateMRMLNodesDeletion = "\n".join(f"slicer.mrmlScene.RemoveNode({name})" for name in intermediateMRMLNodes)
    intermediateMRMLNodesDeletion = intermediateMRMLNodesDeletion or "pass"  # if empty, explicitly call pass

    # note: Tabbing of body is handled by its respective function.
    # note: The extra pass is in case there are no pipeline steps.
    #       This can happen if the purpose of the pipeline is to filter down inputs.
    #       Not sure if this really ever useful, but it is easy to support.
    code = f"""def {functionSignature}:
{tab}# declare needed variables so they exist in the except clause
{textwrap.indent(intermediateMRMLNodesDeclaration, tab)}

{tab}try:
{textwrap.indent(body, tab * 2)}
{tab}{tab}pass
{tab}finally:
{tab}{tab}if delete_intermediate_nodes:
{textwrap.indent(intermediateMRMLNodesDeletion, tab * 3)}

{tab}{returnStatement}"""

    return code, necessaryImports


def createLogic(name: str,
                pipeline: nx.DiGraph,
                registeredPipelines: dict[str, PipelineInfo],
                runFunctionName: str="run",
                tab: str = " " * 4) -> CodePiece:
    """
    Assumes the pipeline has been validated.

    Returns a string which is the python code for the module logic.
    """
    runFunctionCode, runFunctionImports = _generateRunFunction(pipeline, registeredPipelines, runFunctionName, tab)

    constantImports = """
import pickle
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
""".lstrip()
    allImports = cleanupImports(constantImports + runFunctionImports)


    logicCode = f"""#
# {name}
#

class {name}(ScriptedLoadableModuleLogic):
{tab}def __init__(self):
{tab}{tab}ScriptedLoadableModuleLogic.__init__(self)

{tab}# TODO: insert pipeline decorator here
{tab}@staticmethod
{textwrap.indent(runFunctionCode, tab)}
"""

    return CodePiece(imports=allImports, code=logicCode)
