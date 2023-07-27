from typing import Optional, Annotated
from inspect import isclass
import dataclasses

import qt

from Widgets.Types import Reference
from slicer.parameterNodeWrapper import unannotatedType


class ReferenceComboBox(qt.QWidget):
    """
    Combobox for choosing references from a list.
    It is always possible to choose None because the best default action is to not make assumptions.
    Before the final pipeline is actually generated, a non-None choice will need to be made.
    """

    referenceChanged = qt.Signal()

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
        self._combobox.currentIndexChanged.connect(self._onComboBoxIndexChanged)
        self._layout.addWidget(self._combobox)


        # note: this is running through the property setter
        self.references = references or []

    def reset(self) -> None:
        #doesn't seem to trigger index changed signal
        self._combobox.setCurrentIndex(0)

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

    def _onComboBoxIndexChanged(self, index):
        self.referenceChanged.emit()

    @references.setter
    def references(self, references: list[Reference]):
        """
        Sets the new references choices.
        If the currentReferences is in the new list, it will still be chosen.
        If the currentReference is not in the new list, None will be chosen.
        """
        currentRef = self.currentReference
        isBlocking = self._combobox.blockSignals(True)

        unannotatedParamType = unannotatedType(self._paramType)

        #self._inputReferences = [None] + references

        inputReferences = [None]

        #for r in references:
        #    self._inputReferences.append(r)

        if unannotatedParamType == type(None):
            inputReferences += references
        else:
            for r in references:
                # Filters all the references that _could_ be shown to what should be shown
                # The following are eligible
                # - References that don't have a type
                # - The reference that is the current one
                # - Any annotated type whose base type is the same as "mine"
                # - Any type that is a subclass of "mine" (Nodes)
                if r.type == type(None):
                    inputReferences.append(r)
                elif self.currentReference == r:
                    inputReferences.append(r)
                else:
                    if (issubclass(unannotatedType(r.type), unannotatedParamType)):
                        inputReferences.append(r)

        self._inputReferences = inputReferences

        self._combobox.clear()
        self._combobox.addItem("")
        for ref in self._inputReferences[1:]:
            self._combobox.addItem(ref.name)
        try:
            i = self._inputReferences.index(currentRef)
            self._combobox.currentIndex = i
        except ValueError:
            pass

        if currentRef != self.currentReference:
            self.referenceChanged.emit()

        self._combobox.blockSignals(isBlocking)

    @property
    def currentReference(self) -> Optional[Reference]:
        """
        The currently chosen reference, if one is chosen. Otherwise None.
        """
        return self._inputReferences[self._combobox.currentIndex]