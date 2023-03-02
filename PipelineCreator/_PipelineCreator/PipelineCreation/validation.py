import networkx as nx

from _PipelineCreator.PipelineRegistrar import PipelineInfo

from .util import (
    fillInDataTypes,
    groupNodesByStep,
    isReturnNode,
)


def _validatePipelineIsNotEmpty(pipeline: nx.DiGraph) -> None:
    if len(pipeline.nodes) == 0:
        raise ValueError("Cannot have an empty pipeline")


def _validateEachNodeIsFilledOut(pipeline: nx.DiGraph) -> None:
    for node, attributes in pipeline.nodes(data=True):
        if "datatype" not in attributes:
            raise KeyError(f"Pipeline node {node} is missing attribute datatype")


def _validateFixedValuesMatchDataTypes(pipeline: nx.DiGraph) -> None:
    for node, attributes in pipeline.nodes(data=True):
        if "fixed_value" in attributes:
            fixed_value = attributes["fixed_value"]
            datatype = attributes["datatype"]
            if datatype == float and isinstance(fixed_value, int):
                pass  # all implicit conversion from int to float
            elif not isinstance(fixed_value, datatype):
                raise TypeError(f"Pipeline node {node} has fixed value '{fixed_value}' that is not required type '{datatype}'")


def _numSteps(pipeline: nx.DiGraph) -> int:
    """
    Assumes there are no skipped steps
    """
    # the max returns the actual step number. The number of steps is one more than that
    return max(n[0] for n in pipeline.nodes) + 1


def _validateStepPipelineNames(pipeline: nx.DiGraph, registeredPipelines: dict[str, PipelineInfo]) -> None:
    lastStep = _numSteps(pipeline) - 1
    for stepNum, pipelineName, _ in pipeline.nodes:
        if stepNum in (0, lastStep) and pipelineName is not None:
            raise ValueError("The top level and bottom of the pipeline (the overall inputs and outputs of the"
                             " pipeline) are expected have 'None' for the pipelineName")
        elif stepNum not in (0, lastStep) and pipelineName not in registeredPipelines:
            raise ValueError(f"Steps > 1 must have a valid pipeline name:\n  '{pipelineName}' is not registered")


def _validateNoSkippedSteps(pipeline: nx.DiGraph) -> None:
    steps = set()
    for stepNum, _1, _2 in pipeline.nodes:
        steps.add(stepNum)
    if list(steps) != [i for i in range(0, len(steps))]:
        raise ValueError("The given pipeline should have no skipped steps."
                         + f"\nFound steps '{list(steps)}'")


def _validateEachStepIsComplete(pipeline: nx.DiGraph, registeredPipelines: dict[str, PipelineInfo]) -> None:
    grouped = groupNodesByStep(pipeline)
    for group in grouped:
        if any([g[1] != group[0][1] for g in group]):
            raise ValueError("All nodes with the same step should have the same pipeline name")

        pipelineName = group[0][1]
        if pipelineName is not None:
            info = registeredPipelines[pipelineName]

            foundParamNames = sorted([g[2] for g in group if not isReturnNode(g)])
            expectedParamNames = sorted(info.parameters.keys())

            if foundParamNames != expectedParamNames:
                raise ValueError(f"For step {group[0][0]}, pipeline '{pipelineName}', the parameters did not match."
                                + f"\n  Expected {expectedParamNames}, found {foundParamNames}")


def _validateNoBackwardConnections(pipeline: nx.DiGraph) -> None:
    for (fromStep, _1, _2), (toStep, _3, _4) in pipeline.edges:
        if fromStep >= toStep:
            raise ValueError("Cannot connect backwards up a pipeline")


def _validateEachNonFixedInputHasConnection(pipeline: nx.DiGraph) -> None:
    for nodeKey, attributes in pipeline.nodes(data=True):
        step = nodeKey[0]
        isStepOutput = isReturnNode(nodeKey)
        isFixed = "fixed_value" in attributes
        inboundConnections =  len(pipeline.in_edges(nodeKey))
        if step > 0 and not isStepOutput and not isFixed and inboundConnections != 1:
            raise ValueError(f"A non-fixed, non-return node must have exactly 1 input connection. Found {inboundConnections} for {nodeKey}")


def _validateConnectionDataTypes(pipeline: nx.DiGraph) -> None:
    for fromKey, toKey in pipeline.edges:
        fromType = pipeline.nodes[fromKey]["datatype"]
        toType = pipeline.nodes[toKey]["datatype"]

        if fromType == int and toType == float:
            pass # allow going from int to float
        elif not issubclass(fromType, toType):
            raise TypeError(f"Cannot connect from type '{fromType}' to type '{toType}' for nodes {fromKey} to {toKey}")


def validatePipeline(pipeline: nx.DiGraph, registeredPipelines: dict[str, PipelineInfo]) -> None:
    """
    Each node is a 3-tuple of (step#, pipelineName, pipelineVariable).

    Node Attributes:
      datatype: the type of the input or output. Does not need to be specified on steps > 0 (can infer from registeredPipelines)
      fixed_value (optional): if exists, a fixed value will be used instead of
                              a connection
    """
    _validatePipelineIsNotEmpty(pipeline)
    _validateStepPipelineNames(pipeline, registeredPipelines)
    fillInDataTypes(pipeline, registeredPipelines)
    _validateEachNodeIsFilledOut(pipeline)
    _validateEachStepIsComplete(pipeline, registeredPipelines)
    _validateFixedValuesMatchDataTypes(pipeline)
    _validateNoSkippedSteps(pipeline)
    _validateNoBackwardConnections(pipeline)
    _validateEachNonFixedInputHasConnection(pipeline)
    _validateConnectionDataTypes(pipeline)
