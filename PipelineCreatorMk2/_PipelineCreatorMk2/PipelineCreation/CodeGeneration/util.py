import dataclasses
import pickle
import typing

import networkx as nx

from slicer import vtkMRMLNode

@dataclasses.dataclass
class CodePiece:
    imports: str
    code: str


def importCodeForType(type_: type) -> str:
    return f"from {type_.__module__} import {type_.__name__}"


def importCodeForTypes(nodes, pipeline: nx.DiGraph):
    return "\n".join([importCodeForType(pipeline.nodes[n]['datatype']) for n in nodes])


def cleanupImports(importsCode):
    imports = importsCode.split('\n')
    # don't need to explicitly import things from builtins
    imports = [i for i in imports if not i.startswith("from builtins import ")]
    # return unique and sorted
    return "\n".join(sorted(list(set(imports))))


def typeAsCode(type_: type) -> str:
    """
    Takes common types and returns the type as it is written in code.
    """
    if type_ == int:
        return "int"
    if type_ == float:
        return "float"
    if type_ == str:
        return "str"
    if type_ == bool:
        return "bool"
    origin = typing.get_origin(type_)
    args = typing.get_args(type_)
    if origin == list:
        assert len(args) == 1, f"Expected list to have 1 arg, found {args}"
        return f"list[{typeAsCode(args[0])}]"
    if origin == dict:
        assert len(args) == 2, f"Expected dict to have 2 args, found {args}"
        return f"dict[{typeAsCode(args[0])}, {typeAsCode(args[1])}]"
    if origin == tuple:
        assert len(args) > 0, "Expected tuple to have at least one arg"
        tupleArgs = ", ".join([typeAsCode(arg) for arg in args])
        return f"tuple[{tupleArgs}]"

    # unfortunately, MRML node types are not pickle-able
    if issubclass(type_, vtkMRMLNode):
        return type_.__name__

    # last ditch, pickle the type
    return f"pickle.loads({pickle.dumps(type_)})"


def valueAsCode(value) -> str:
    """
    The only goal of this is to improve generated code readability 
    (and even that is mostly for testing)
    """
    type_ = type(value)
    if type_ in (int, float, bool):
        return str(value)
    if type_ == str:
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join([valueAsCode(v) for v in value]) + "]"

    # just pickle other complex types
    return f"pickle.loads({pickle.dumps(value)})"
