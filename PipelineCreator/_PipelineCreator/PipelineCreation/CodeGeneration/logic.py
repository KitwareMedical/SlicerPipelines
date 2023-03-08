import itertools
import networkx as nx
import pickle
import re
import textwrap
from typing import Union

import slicer

from slicer.parameterNodeWrapper import unannotatedType

from _PipelineCreator.PipelineRegistrar import PipelineInfo

from _PipelineCreator.PipelineCreation.util import (
    getStep,
    groupNodesByStep,
    splitParametersFromReturn,
)
from _PipelineCreator.PipelineCreation.CodeGeneration.util import (
    CodePiece,
    cleanupImports,
    importCodeForType,
    importCodeForTypes,
    typeAsCode,
    valueAsCode,
)

__all__ = ["createLogic"]


def _getReturnType(lastStepNodes, fullPipeline, compositeReturnTypeClassName):
    assert len(lastStepNodes) != 0
    if len(lastStepNodes) == 1:
        return fullPipeline.nodes[lastStepNodes[0]]['datatype']
    else:
        return compositeReturnTypeClassName


def _makeToplevelFunctionSignature(functionName, fullPipeline, returnType: Union[str, type]) -> str:
    returnTypeCode = returnType if isinstance(returnType, str) else typeAsCode(returnType)
    params, _ = getStep(0, fullPipeline)
    parameterString = ", ".join(f"{param[2]}: {typeAsCode(fullPipeline.nodes[param]['datatype'])}"
                                for param in params)
    necessaryImports = "from PipelineCreator import PipelineProgressCallback\n" + importCodeForTypes(params, fullPipeline)
    if not isinstance(returnType, str):
        necessaryImports += "\n" + importCodeForType(returnType)
    return f"{functionName}({parameterString}, *, progress_callback=PipelineProgressCallback(), delete_intermediate_nodes=True) -> {returnTypeCode}", necessaryImports


def _varName(node) -> str:
    step = node[0]
    if step == 0:
        # function signature gets nicer names
        return node[2]  # paramName
    else:
        # step_{step#}_{pipelineName}_{paramName}
        # e.g. step_1_cleanPolyData_return
        #      step_1_somePipe_return.packSubItem
        cleanedPipelineName = _cleanPipelineName(node=node)
        # note: node[2] could have a . to get at a subitem
        return f"step_{node[0]}_{cleanedPipelineName}_{node[2]}"


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


def _generateStepCode(step, pipeline: nx.DiGraph, registeredPipelines: dict[str, PipelineInfo], numSteps, tab: str) -> str:
    """
    Each output node is given a well known variable name by the 
    """
    parameters, returns = splitParametersFromReturn(step)
    stepArguments = [
        f"{node[2]}={_getInput(node, pipeline)}" for node in parameters
    ]
    stepArgumentsCode = textwrap.indent(",\n".join(stepArguments), tab)

    # get the returns, but filter out anything that is a break down of a parameterPack
    returnVariables = list(set([r.split('.')[0] for r in _returnVarNames(returns)]))
    if len(returnVariables) != 1:
        raise RuntimeError(f"Unexpected number of returns: {returnVariables}")

    stepFunctionName = _stepFunctionName(step)
    stepFunctionValue = _stepFunctionValue(step, registeredPipelines)

    progressCallbackName = registeredPipelines[step[0][1]].progressCallbackName
    if progressCallbackName is not None:
        progressStr = f",\n{progressCallbackName}=progress_callback.getSubCallback({step[0][0] - 1}, {numSteps})"
    else:
        progressStr = ""

    stepCode = f"""# step {step[0][0]} - {step[0][1]}
progress_callback.reportProgress("{step[0][1]}", 0, {step[0][0] - 1}, {numSteps})
{stepFunctionName} = {stepFunctionValue}
{returnVariables[0]} = {stepFunctionName}(
{stepArgumentsCode}{progressStr})
"""
    return stepCode


def _getReturnedVariables(lastStep, pipeline: nx.DiGraph):
    return [_getInput(n, pipeline) for n in lastStep]


def _generateReturnStatement(lastStep, pipeline: nx.DiGraph, compositeReturnClassName: str) -> str:
    if len(lastStep) == 1:
        return f"return {_getReturnedVariables(lastStep, pipeline)[0]}"
    else:
        lastStep.sort(key=lambda node: pipeline.nodes[node]["position"])
        args = ", ".join(_getReturnedVariables(lastStep, pipeline))
        return f"return {compositeReturnClassName}({args})"


def _isPartOfReturn(name, returnVars):
    if name in returnVars:
        return True
    if name.split('.')[0] in returnVars:
        return True
    if name in [r.split('.')[0] for r in returnVars]:
        return True
    return False


def _splitIntermediatesFromReturns(pipeline: nx.DiGraph):
    steps = groupNodesByStep(pipeline)
    mrmlReturnNames = []
    for step in steps:
        _, returns = splitParametersFromReturn(step)
        mrmlReturns = [ret for ret in returns if issubclass(unannotatedType(pipeline.nodes[ret]["datatype"]), slicer.vtkMRMLNode)]
        mrmlReturnNames += _returnVarNames(mrmlReturns)

    # remove returned variables, so we only have intermediates
    returnVars = _getReturnedVariables(steps[-1], pipeline)
    intermediates = [m for m in mrmlReturnNames if not _isPartOfReturn(m, returnVars)]
    trueReturns = [m for m in mrmlReturnNames if _isPartOfReturn(m, returnVars)]

    # reduce parameterPack items to just the top level pack
    notInAContainer = [m for m in intermediates if not '.' in m]
    inAContainer = [m for m in intermediates if '.' in m]
    return notInAContainer, inAContainer, trueReturns


def _generateDeleteIntermediatesCode(pipeline: nx.DiGraph, tab: str):
    intermediateMRMLNodesNotInContainer, intermediateMRMLNodesInContainer, trueReturns = _splitIntermediatesFromReturns(pipeline)
    intermediateContainers = list(set(m.split(".")[0] for m in intermediateMRMLNodesInContainer))

    declaration = '\n'.join([f"{name} = None"
                             for name in itertools.chain(intermediateMRMLNodesNotInContainer, intermediateContainers, trueReturns)
                             if not '.' in name])


    deletion = f"trueReturns = [{','.join(trueReturns)}]\n" 
    deletion += "\n".join(f"slicer.mrmlScene.RemoveNode({name})" for name in intermediateMRMLNodesNotInContainer)
    for i in intermediateMRMLNodesInContainer:
        container = i.split(".")[0]
        deletion += f"\nif {container} is not None and not _nodeReferencedBy({i}, trueReturns):\n{tab}slicer.mrmlScene.RemoveNode({i})"

    deletion = deletion or "pass"  # if empty, explicitly call pass

    return declaration, deletion


def _generateRunFunction(pipeline: nx.DiGraph,
                         registeredPipelines: dict[str, PipelineInfo],
                         runFunctionName: str,
                         compositeReturnTypeClassName: str,
                         tab: str) -> tuple[str, str]:
    """
    Returns (function-code, necessary-imports)
    """
    steps = groupNodesByStep(pipeline)
    returnType = _getReturnType(steps[-1], pipeline, compositeReturnTypeClassName)
    functionSignature, necessaryImports = _makeToplevelFunctionSignature(runFunctionName, pipeline, returnType)
    body = "\n".join(_generateStepCode(step, pipeline, registeredPipelines, len(steps) - 2, tab) for step in steps[1:-1])
    returnStatement = _generateReturnStatement(steps[-1], pipeline, compositeReturnTypeClassName)

    intermediateMRMLNodesDeclaration, intermediateMRMLNodesDeletion = _generateDeleteIntermediatesCode(pipeline, tab)

    numSteps = max(1, len(steps) - 2)

    # note: Tabbing of body is handled by its respective function.
    # note: The extra pass is in case there are no pipeline steps.
    #       This can happen if the purpose of the pipeline is to filter down inputs.
    #       Not sure if this really ever useful, but it is easy to support.
    code = f"""def {functionSignature}:
{tab}progress_callback.reportProgress("", 0, 0, {numSteps})
{tab}# declare needed variables so they exist in the finally clause
{textwrap.indent(intermediateMRMLNodesDeclaration, tab)}

{tab}try:
{textwrap.indent(body, tab * 2)}
{tab}{tab}pass
{tab}finally:
{tab}{tab}if delete_intermediate_nodes:
{textwrap.indent(intermediateMRMLNodesDeletion, tab * 3)}

{tab}progress_callback.reportProgress("", 0, {numSteps}, {numSteps})

{tab}{returnStatement}"""

    return code, necessaryImports


def createLogic(name: str,
                pipeline: nx.DiGraph,
                registeredPipelines: dict[str, PipelineInfo],
                parameterNodeOutputsName: str,
                runFunctionName: str="run",
                tab: str = " " * 4) -> CodePiece:
    """
    Assumes the pipeline has been validated.

    Returns a string which is the python code for the module logic.
    """
    runFunctionCode, runFunctionImports = _generateRunFunction(pipeline, registeredPipelines, runFunctionName, parameterNodeOutputsName, tab)

    constantImports = """
import pickle
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
""".lstrip()
    allImports = cleanupImports(constantImports + runFunctionImports)

    logicCode = f"""#
# {name}
#

def _nodeReferencedBy(node, listOfNodes):
{tab}for option in listOfNodes:
{tab}{tab}if option is not None:
{tab}{tab}{tab}roles = []
{tab}{tab}{tab}option.GetNodeReferenceRoles(roles)
{tab}{tab}{tab}for role in roles:
{tab}{tab}{tab}{tab}if option.HasNodeReferenceID(role, node.GetID()):
{tab}{tab}{tab}{tab}{tab}return True
{tab}return False

class {name}(ScriptedLoadableModuleLogic):
{tab}def __init__(self):
{tab}{tab}ScriptedLoadableModuleLogic.__init__(self)

{tab}# TODO: insert pipeline decorator here
{tab}@staticmethod
{textwrap.indent(runFunctionCode, tab)}
"""

    return CodePiece(imports=allImports, code=logicCode)
