import dataclasses

@dataclasses.dataclass
class PipelineParameter:
    """Represents a specific input parameter of a specific pipeline stage, is used so that references can
    be connected to input parameters without involving the UI classes, more generally its a
    _receiver_ of values through the pipeline"""

    # identify the parameter
    # id is equivalent to the index of the parameter in the function declaration
    owner: object   # Most likely a pipeline step
    id: int

    parametername: str  # name of this parameter
    type: type = type(None)

    def __eq__(self, other) -> bool:
        return isinstance(other, PipelineParameter) and self.owner == other.owner and self.id == other.id



@dataclasses.dataclass
class Reference:
    """Represents a source of values that may be used as input to a step or a final result.
    This can be the result of a step or the overall inputs to the pipeline.
    """
    # Identifying pieces. Cannot change.
    owner: object
    id: int

    # Informational pieces. Can change.
    step: int
    stepName: str
    referenceName: str
    type: type = type(None)

    def __eq__(self, other) -> bool:
        return isinstance(other, Reference) and self.owner == other.owner and self.id == other.id

    @property
    def name(self) -> str:
        return f"step{self.step}_{self.stepName}_{self.referenceName}"

