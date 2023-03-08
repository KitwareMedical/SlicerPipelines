import dataclasses
import itertools
import pickle
import typing

import networkx as nx

from slicer.parameterNodeWrapper import unannotatedType

from _PipelineCreator.PipelineRegistrar import PipelineInfo


__all__ = []


def groupNodesByStep(pipeline: nx.DiGraph) -> list[list[tuple[int, str, str]]]:
    nodes = sorted(pipeline.nodes)
    return [list(group) for _, group in itertools.groupby(nodes, lambda x: x[0])]


def numSteps(pipeline: nx.DiGraph) -> int:
    steps = groupNodesByStep(pipeline)
    if steps:
        # size is last index + 1
        return steps[-1][0][0] + 1
    else:
        return 0

def isReturnParam(paramName: str):
    return paramName == "return" or paramName.startswith("return.")


def isReturnNode(node: tuple[int, str, str]):
    return isReturnParam(node[2])


def splitParametersFromReturn(step):
    """
    A step is a list of all nodes that have the same step value.

    Returns (parameters, returns)
    """
    return (
        [n for n in step if not isReturnNode(n)],
        [n for n in step if isReturnNode(n)],
    )


def getStep(stepIndex: int, pipeline: nx.DiGraph):
    """
    A step is a list of all nodes that have the same step value.

    If the parameter nodes have the "position" attribute set, they will be sorted in that order.

    Returns (parameters-in-order, returns)
    """
    # support negative indexes
    if stepIndex < 0:
        stepCount = numSteps(pipeline)
        stepIndex = stepCount + stepIndex

    stepNodes = [n for n in pipeline.nodes() if n[0] == stepIndex]
    params, returns = splitParametersFromReturn(stepNodes)

    if params and "position" in pipeline.nodes[params[0]]:
        positions = [pipeline.nodes[n]['position'] for n in params]
        # sort two parallel lists together
        params, positions = zip(*sorted(zip(params, positions), key=lambda x: x[1]))

        if positions != tuple(range(0, len(params))):
            raise ValueError("Top level inputs are expected to have a 'position' attribute that indicates"
                            f" the position of the argument in the function. Found positions {positions}")

    return params, returns


def fillInDataTypes(pipeline: nx.DiGraph, registeredPipelines: dict[str, PipelineInfo]) -> None:
     for (_, pipelineName, paramName), attributes in pipeline.nodes(data=True):
        if pipelineName is not None:
            info = registeredPipelines[pipelineName]
            if isReturnParam(paramName):
                if '.' in paramName:
                    # piece of a parameter pack
                    datatype = unannotatedType(unannotatedType(info.returnType).dataType(paramName.split('.', maxsplit=1)[1]))
                else:
                    datatype = unannotatedType(info.returnType)
            else:
                datatype = unannotatedType(info.parameters[paramName])
            if "datatype" in attributes and attributes["datatype"] != datatype:
                raise TypeError(f"Found specified datatype that does not match known datatype\n  {attributes['datatype']} vs {datatype}")
            attributes["datatype"] = datatype


def printPipeline(pipeline: nx.DiGraph) -> None:
    """
    Prints a somewhat readable text representation of the pipeline.
    """
    print(pipeline.nodes)
    print("Nodes:")
    for s in range(numSteps(pipeline)):
        params, returns = getStep(s, pipeline)
        for param in params:
            print("  ", param, pipeline.nodes[param])
        for ret in returns:
            print("  ", ret, pipeline.nodes[ret])

    #TODO: Sort by to-step and then sort each to-step by position
    print("Edges:")
    for from_, to in pipeline.edges:
        print("  Edge:")
        print("    ", from_)
        print("    ", to)

