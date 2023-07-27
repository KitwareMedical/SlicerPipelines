import qt
import ctk

from Widgets.Types import Reference
from Widgets.ReferenceComboBox import ReferenceComboBox

class PipelineOutputParameterWidget(qt.QWidget):
    """
    This class represents a single _overall_ pipeline output.

    This duck type matches PipelineStepParameterWidgets (but since fixed is always false, it doesn't have computeFixedValue)
    """
    valueChanged = qt.Signal()
    requestedDelete = qt.Signal()

    def __init__(self, name: str, parent=None):
        """
        name - The starting name fo the overall output.
        parent - The widget's parent.
        """
        qt.QWidget.__init__(self, parent)

        self._mainLayout = qt.QHBoxLayout(self)

        self.nameWidget = qt.QLineEdit(name)
        self.nameWidget.textChanged.connect(self._emitValueChanged)

        self.referenceWidget = ReferenceComboBox()
        self.referenceWidget.sizePolicy = qt.QSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
        self.referenceWidget.referenceChanged.connect(self._emitValueChanged)

        self.deleteButton = qt.QPushButton(qt.QIcon(":/Icons/MarkupsDelete.png"), "")
        self.deleteButton.clicked.connect(self._emitRequestedDelete)

        self._mainLayout.addWidget(self.nameWidget)
        self._mainLayout.addWidget(self.referenceWidget)
        self._mainLayout.addWidget(self.deleteButton)

    @property
    def name(self) -> str:
        return self.nameWidget.text

    @name.setter
    def name(self, text: str) -> None:
        self.nameWidget.text = text

    @property
    def fixed(self) -> bool:
        return False

    @property
    def currentReference(self) -> Reference:
        return self.referenceWidget.currentReference

    def updateReferences(self, references) -> None:
        self.referenceWidget.references = references

    def _emitValueChanged(self):
        self.valueChanged.emit()

    def _emitRequestedDelete(self):
        self.requestedDelete.emit()

    def _updateTypes(self):
        text = self.typesWidget.currentText
        typesAsStrs = [t.__name__ for t in self.availableTypes]
        self.typesWidget.clear()
        self.typesWidget.addItems(typesAsStrs)
        # set to what it was before, it is still there
        self.typesWidget.currentText = text
        self._emitValueChanged()


class PipelineOutputWidget(qt.QWidget):
    valueChanged = qt.Signal()

    def __init__(self, stepNumber, stepName, defaultName, parent=None) -> None:
        qt.QWidget.__init__(self, parent)

        self._stepNumber = stepNumber
        self.stepName = stepName
        self.defaultName = defaultName

        self._mainLayout = qt.QVBoxLayout(self)

        self._collapsibleButton = ctk.ctkCollapsibleButton()
        self._collapsibleButton.setProperty("PipelineStepCollapsible", True)
        self._mainLayout.addWidget(self._collapsibleButton)
        self._collapsibleButton.setLayout(qt.QVBoxLayout())
        self._collapsibleButton.setText(f"Step {self.stepNumber} - {self.stepName}")
        self._collapsibleButton.collapsed = False

        addButton = qt.QPushButton("+")
        addButton.sizePolicy = qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        addButton.clicked.connect(lambda: self._addParameter())
        self._collapsibleButton.layout().addWidget(addButton)

        self._setupOutputContainer()

    @property
    def stepNumber(self) -> int:
        return self._stepNumber

    @stepNumber.setter
    def stepNumber(self, num: int) -> None:
        self._stepNumber = num
        self._collapsibleButton.text = f"Step {self._stepNumber} - {self.stepName}"

    @property
    def inputs(self) -> list[PipelineOutputParameterWidget]:
        return self._parameterWidgets

    def updateInputReferences(self, inputReferences):
        for paramWidget in self._parameterWidgets:
            paramWidget.updateReferences(inputReferences)

    def _emitValueChanged(self):
        self.valueChanged.emit()

    @property
    def stepOutputs(self) -> list[Reference]:
        """The output widget doesn't have any outputs"""
        return []

    @property
    def _parameterWidgets(self) -> list[PipelineOutputParameterWidget]:
        layout = self._parameterContainer.layout()
        return [layout.itemAt(i).widget() for i in range(1, layout.count())]

    def _addParameter(self, name=None) -> None:
        layout = self._parameterContainer.layout()

        name = name if name is not None else f"{self.defaultName}{layout.count()}"
        paramWidget = PipelineOutputParameterWidget(name)
        paramWidget.valueChanged.connect(self._emitValueChanged)
        paramWidget.requestedDelete.connect(lambda: self._removeParameter(paramWidget))

        layout.addWidget(paramWidget)
        self.valueChanged.emit()

    def _removeParameter(self, widget) -> None:
        layout = self._parameterContainer.layout()
        widget.hide()
        widget.valueChanged.disconnect(self._emitValueChanged)
        layout.removeWidget(widget)
        widget.deleteLater()
        self.valueChanged.emit()

    def _setupOutputContainer(self) -> None:
        self._parameterContainer = qt.QWidget()
        self._collapsibleButton.layout().addWidget(self._parameterContainer)
        self._parameterContainer.setLayout(qt.QVBoxLayout())

        headerWidget = qt.QWidget()
        headerWidget.setLayout(qt.QHBoxLayout())
        nameLabel = qt.QLabel("Name")
        headerWidget.layout().addWidget(nameLabel)
        typeLabel = qt.QLabel("Value")
        headerWidget.layout().addWidget(typeLabel)

        self._parameterContainer.layout().addWidget(headerWidget)

        # add one item
        self._addParameter()

