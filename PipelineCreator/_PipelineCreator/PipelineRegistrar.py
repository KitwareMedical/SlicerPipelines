import dataclasses
import inspect
import typing

from slicer.parameterNodeWrapper import (
    unannotatedType,
)

__all__ = [
    "PipelineInfo",
    "PipelineRegistrar",
]

@dataclasses.dataclass
class PipelineInfo:
    name: str
    function: typing.Callable
    parameters: dict[str, typing.Any]  # key: parameter name, value: type of parameter (could be annotated)
    returnType: typing.Any  # Some kind of type, but it could be annotated
    progressCallbackName: typing.Optional[str]
    dependencies: list[str]
    categories: list[str]


class PipelineRegistrar:
    def __init__(self) -> None:
        # Users outside this class should only read this, not write directly to it
        self.registeredPipelines: dict[str, PipelineInfo] = dict()

    def isRegistered(self, pipelineName: str) -> bool:
        return pipelineName in self.registeredPipelines

    @staticmethod
    def validatePipelineFunction(function) -> None:
        typehints = typing.get_type_hints(function, include_extras=False)
        signature = inspect.signature(function)

        # validate return type is annotated
        if "return" not in typehints:
            raise RuntimeError(f"Pipelined function {function} does not have an annotated return type")

        # validate we actually return something
        if isinstance(None, typehints["return"]):
            raise RuntimeError(f"Pipelined function {function} cannot have None as the return type")

        # validate all parameters are annotated
        for parameter in signature.parameters:
            if parameter not in typehints:
                raise RuntimeError(f"Pipelined function {function} has unannotated parameter '{parameter}")

    @property
    def pipelinedTypes(self):
        """
        Get all types used as inputs or outputs for all pipelines
        """
        types = set()
        for info in self.registeredPipelines.values():
            #TODO: break apart parameter packs?
            for param in info.parameters.values():
                types.add(unannotatedType(param))
            types.add(unannotatedType(info.returnType))
        return types

    def registerPipeline(self, name: str, function, dependencies, categories=None) -> None:
        """
        Registers a pipeline for use.

        function: A type annotated function to make a pipeline of
        """
        from PipelineCreator import isPipelineProgressCallback

        if name in self.registeredPipelines:
            raise RuntimeError(f"Cannot register pipeline with duplicate name '{name}'")

        self.validatePipelineFunction(function)

        typehints = typing.get_type_hints(function, include_extras=True)
        parameterHints = {key: value for key, value in typehints.items() if key != "return"}
        returnHint = typehints["return"]

        progressCallbacks = {key: value for key, value in parameterHints.items() if isPipelineProgressCallback(value)}
        parameterHints = {key: value for key, value in parameterHints.items() if not isPipelineProgressCallback(value)}

        if len(progressCallbacks) == 0:
            progressCallbackName = None
        else:
            progressCallbackName = next(iter(progressCallbacks.keys()))

        info = PipelineInfo(name, function, parameterHints, returnHint, progressCallbackName, dependencies, categories or [])
        self.registeredPipelines[name] = info
