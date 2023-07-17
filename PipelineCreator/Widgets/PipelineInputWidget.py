import qt
import ctk

from Widgets.ReferenceComboBox import Reference

class PipelineInputParameterWidget(qt.QWidget):
    """
    This widget represents a single _overall_ input to the _entire_ constructed pipeline.
    """
    valueChanged = qt.Signal()
    requestedDelete = qt.Signal()

    def __init__(self, id_: int, stepNumber: int, name: str, availableTypes: list[type]=None, type_: type = None, parent=None):
        """
        id_ - An unique identifier for this overall input parameter. Will be used for identifying this parameter's reference.
        stepNumber - Should always be 0 because this is an overall input.
        name - Starting name of the parameter
        availableTypes - List of types to choose from for this overall input parameter.
        type_ - The starting type. Should be in the availableTypes.
        parent - The parent widget.
        """
        qt.QWidget.__init__(self, parent)

        self.id = id_
        self.stepNumber = stepNumber
        self._availableTypes = availableTypes

        self._mainLayout = qt.QHBoxLayout(self)

        self.nameWidget = qt.QLineEdit(name)
        self.nameWidget.textChanged.connect(self._emitValueChanged)

        self.typesWidget = qt.QComboBox()
        self.typesWidget.sizePolicy = qt.QSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
        self._updateTypes()
        if type_ is not None:
            self.typesWidget.currentIndex = self.availableTypes.index(type_)
        self.typesWidget.currentIndexChanged.connect(self._emitValueChanged)

        self.deleteButton = qt.QPushButton(qt.QIcon(":/Icons/MarkupsDelete.png"), "")
        self.deleteButton.clicked.connect(self._emitRequestedDelete)

        self._mainLayout.addWidget(self.nameWidget)
        self._mainLayout.addWidget(self.typesWidget)
        self._mainLayout.addWidget(self.deleteButton)

    @property
    def availableTypes(self) -> list[type]:
        return self._availableTypes

    @availableTypes.setter
    def availableTypes(self, types: list[type]) -> None:
        self._availableTypes = list(types)
        self._updateTypes()

    @property
    def reference(self) -> Reference:
        """
        Get the reference that will link to value described by this widget.
        """
        return Reference(self, self.id, self.stepNumber, None, self.nameWidget.text, self.availableTypes[self.typesWidget.currentIndex])

    def _emitValueChanged(self) -> None:
        self.valueChanged.emit()

    def _emitRequestedDelete(self) -> None:
        self.requestedDelete.emit()

    def _updateTypes(self):
        """
        Updates the typesWidget with new types to choose from.
        Completely replaces the old list.
        """
        text = self.typesWidget.currentText
        typesAsStrs = [t.__name__ for t in self.availableTypes]
        self.typesWidget.clear()
        self.typesWidget.addItems(typesAsStrs)
        # set to what it was before, if it is still there
        self.typesWidget.currentText = text
        self._emitValueChanged()


class PipelineInputWidget(qt.QWidget):
    """
    Widget that represents _all overall_ inputs to the entire pipeline.

    This duck type matches the stepOutputs portion of the PipelineStepWidget.
    """
    valueChanged = qt.Signal()

    def __init__(self, stepNumber: int, displayStepName: str, defaultName: str, availableTypes: list[type]=None, parent=None) -> None:
        """
        stepNumber - Should always be 0 because this is the overall input.
        displayStepName - The step name that should display on the collapsible button. Note: for DiGraph pipeline descriptions,
                          the stepName for overall inputs and outputs is None (the value, not the string).
        defaultName - The default basename for new inputs. A number will appended to them.
        availableTypes - List of types to choose from for this overall input parameter.
        parent - The parent widget.
        """
        qt.QWidget.__init__(self, parent)

        self._availableTypes = list(availableTypes) or []
        self._stepNumber = stepNumber
        self.displayStepName = displayStepName
        self.defaultName = defaultName

        self._mainLayout = qt.QVBoxLayout(self)

        self._parameterId = 0

        self._collapsibleButton = ctk.ctkCollapsibleButton()
        self._collapsibleButton.setProperty("PipelineStepCollapsible", True)
        self._mainLayout.addWidget(self._collapsibleButton)
        self._collapsibleButton.setLayout(qt.QVBoxLayout())
        self._collapsibleButton.setText(f"Step {self.stepNumber} - {self.displayStepName}")
        self._collapsibleButton.collapsed = False

        addButton = qt.QPushButton("+")
        addButton.sizePolicy = qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        addButton.clicked.connect(lambda: self._addParameter())
        self._collapsibleButton.layout().addWidget(addButton)

        self._setupInputContainer()

    @property
    def _parameterWidgets(self) -> list[PipelineInputParameterWidget]:
        layout = self._parameterContainer.layout()
        return [layout.itemAt(i).widget() for i in range(1, layout.count())]

    @property
    def stepOutputs(self) -> list[Reference]:
        """
        The intermediate output references for this step.
        """
        return [p.reference for p in self._parameterWidgets]

    @property
    def availableTypes(self) -> list[type]:
        return self._availableTypes

    @availableTypes.setter
    def availableTypes(self, types: list[type]) -> None:
        self._availableTypes = list(types)
        for p in self._parameterWidgets:
            p.availableTypes = self.availableTypes

    @property
    def stepNumber(self) -> int:
        return self._stepNumber

    @stepNumber.setter
    def stepNumber(self, num: int) -> None:
        self._stepNumber = num
        self._collapsibleButton.text = f"Step {self._stepNumber} - {self.stepName}"

    def _emitValueChanged(self) -> None:
        self.valueChanged.emit()

    def _addParameter(self, name=None, type_=None) -> None:
        """
        Adds a new input parameter.
        If name and type are not None, they will be used for the new parameter.
        """
        layout = self._parameterContainer.layout()

        name = name if name is not None else f"{self.defaultName}{layout.count()}"
        paramWidget = PipelineInputParameterWidget(self._parameterId, self.stepNumber, name, self.availableTypes, type_)
        paramWidget.valueChanged.connect(self._emitValueChanged)
        paramWidget.requestedDelete.connect(lambda: self._removeParameter(paramWidget))

        self._parameterId += 1

        layout.addWidget(paramWidget)

        self.valueChanged.emit()

    def _removeParameter(self, widget: PipelineInputParameterWidget):
        """
        Removes a parameter.
        widget - The PipelineInputParameterWidget to remove
        """
        layout = self._parameterContainer.layout()
        widget.hide()
        widget.valueChanged.disconnect(self._emitValueChanged)
        layout.removeWidget(widget)
        widget.deleteLater()
        self.valueChanged.emit()

    def _setupInputContainer(self):
        """
        Sets up headers for the input parameters, and adds one parameter by default.
        """
        self._parameterContainer = qt.QWidget()
        self._collapsibleButton.layout().addWidget(self._parameterContainer)
        self._parameterContainer.setLayout(qt.QVBoxLayout())

        headerWidget = qt.QWidget()
        headerWidget.setLayout(qt.QHBoxLayout())
        nameLabel = qt.QLabel("Name")
        headerWidget.layout().addWidget(nameLabel)
        typeLabel = qt.QLabel("Type")
        headerWidget.layout().addWidget(typeLabel)

        self._parameterContainer.layout().addWidget(headerWidget)

        # add one item
        self._addParameter()

