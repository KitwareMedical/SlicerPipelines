import dataclasses
import qt

from typing import Optional

from slicer.parameterNodeWrapper import unannotatedType

@dataclasses.dataclass
class Reference:
    """
    A reference to an intermediate output.

    Note: the overall inputs count as intermediate outputs because they can be used as
    inputs to subsequent steps.
    """
    # Identifying pieces. Cannot change.
    obj: object
    id: int

    # Informational pieces. Can change.
    step: int
    stepName: str
    itemName: str
    type: type

    def __eq__(self, other) -> bool:
        return isinstance(other, Reference) and self.obj == other.obj and self.id == other.id

    @property
    def name(self) -> str:
        return f"step{self.step}_{self.stepName}_{self.itemName}"

class ReferenceComboBox(qt.QWidget):
    """
    Combobox for choosing references from a list.
    It is always possible to choose None because the best default action is to not make assumptions.
    Before the final pipeline is actually generated, a non-None choice will need to be made.
    """
    currentIndexChanged = qt.Signal()

    def __init__(self, paramType: Optional[type]=None, references=None, parent=None):
        """
        paramType - The allowed type(s) of the references to choose from. None means allow any type.
        references - The reference options. This class will take of filtering this down to match the paramType.
        parent - The widget's parent
        """
        super().__init__(parent)

        self._paramType = paramType
        self._inputReferences = [None]

        self._layout = qt.QVBoxLayout(self)
        self._combobox = qt.QComboBox()
        self._layout.addWidget(self._combobox)

        # note: this is running through the property setter
        self.references = references or []

    @property
    def paramType(self) -> type:
        """
        The allowed type(s) of the references to choose from. None means allow any type.
        """
        return self._paramType

    @property
    def references(self) -> list[Reference]:
        """
        The list of references choices that match the paramType.
        """
        return self._inputReferences[1:]

    @references.setter
    def references(self, references: list[Reference]):
        """
        Sets the new references choices.
        If the currentReferences is in the new list, it will still be chosen.
        If the currentReference is not in the new list, None will be chosen.
        """
        currentRef = self.currentReference

        unannotatedParamType = unannotatedType(self.paramType)
        if unannotatedParamType == type(None):
            self._inputReferences = [None] + references
        else:
            self._inputReferences = [None] + [r for r in references if issubclass(r.type, unannotatedParamType)]

        self._combobox.clear()
        self._combobox.addItem("")
        for ref in self._inputReferences[1:]:
            self._combobox.addItem(ref.name)

        try:
            i = self._inputReferences.index(currentRef)
            self._combobox.currentIndex = i
        except ValueError:
            pass

    @property
    def currentReference(self) -> Optional[Reference]:
        """
        The currently chosen reference, if one is chosen. Otherwise None.
        """
        return self._inputReferences[self._combobox.currentIndex]