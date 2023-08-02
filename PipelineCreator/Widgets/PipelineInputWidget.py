import qt
import ctk

from typing import Optional, Annotated, get_origin

from _PipelineCreator.PipelineCreation.CodeGeneration.util import annotatedAsCode
from slicer.parameterNodeWrapper import unannotatedType
from slicer import vtkMRMLNode


from Widgets.Types import Reference, PipelineParameter

class PipelineInputParameterWidget(qt.QWidget):
    """
    This widget represents a single _overall_ input to the _entire_ constructed pipeline.
    """
    valueChanged = qt.Signal()
    requestedDelete = qt.Signal()

    def __init__(self, id: int, stepNumber: int, name: str, availableTypes: list[type]=None, type_: type = None, parent=None):
        """
        id_ - An unique identifier for this overall input parameter. Will be used for identifying this parameter's reference.
        stepNumber - Should always be 0 because this is an overall input.
        name - Starting name of the parameter
        availableTypes - List of types to choose from for this overall input parameter.
        type_ - The starting type. Should be in the availableTypes.
        parent - The parent widget.
        """
        qt.QWidget.__init__(self, parent)

        self.id = id
        self.stepNumber = stepNumber
        self._availableTypes = availableTypes
        self._referencing: list[PipelineParameter] = []
        self._type = type(None)

        self._mainLayout = qt.QHBoxLayout(self)

        self.nameWidget = qt.QLineEdit(name)
        self.nameWidget.textChanged.connect(self._emitValueChanged)
        self.typeLabel = qt.QLabel()
        self.typeLabel.sizePolicy = qt.QSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)

        self.deleteButton = qt.QPushButton(qt.QIcon(":/Icons/MarkupsDelete.png"), "")
        self.deleteButton.clicked.connect(self._emitRequestedDelete)

        self._mainLayout.addWidget(self.nameWidget)
        self._mainLayout.addWidget(self.typeLabel)
        self._mainLayout.addWidget(self.deleteButton)

    def addReferencing(self, pipelineParameter: PipelineParameter):
        """Adds a reference _from_ widget to this, types have to match"""
        if (self.type != type(None) and unannotatedType(self.type) != unannotatedType(pipelineParameter.type)):
            raise TypeError(f"Parameter {self.nameWidget.text} does not have the same type as {pipelineParameter}")

        if not pipelineParameter in self._referencing:
            self._referencing.append(pipelineParameter)

        if self.type == type(None):
            self.type = pipelineParameter.type
            self.valueChanged.emit()

    def removeReferencing(self, pipelineParameter: PipelineParameter):
        """Removes the reference _to_ the parameters given from this input"""
        if pipelineParameter in self._referencing:
            self._referencing.remove(pipelineParameter)

        if len(self._referencing) == 0:
            self.type = type(None)
            self.valueChanged.emit()

    def _updateTypeLabel(self, paramType : type) -> None:
        """Try and give the user a reasonable description of the type
        assigned to this input parameter"""
        if paramType == type(None):
            self.typeLabel.text = ""
        else:
            if get_origin(paramType) is Annotated or issubclass(paramType, vtkMRMLNode):
                text = annotatedAsCode(paramType)
                if len(text) > 50:
                    text = text[:46] + " ..."
                self.typeLabel.text = text
            else:
                self.typeLabel.text = paramType.__name__

    @property
    def type(self) -> type:
        return self._type

    @type.setter
    def type(self, type: type) -> None:
        self._type = type
        self._updateTypeLabel(self._type)

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
        return Reference(self, self.id, self.stepNumber, None, self.nameWidget.text, self._type)

    def _emitValueChanged(self) -> None:
        self.valueChanged.emit()

    def _emitRequestedDelete(self) -> None:
        self.requestedDelete.emit()



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

    def addReferencing(self, reference: Reference, pipelineParameter: PipelineParameter):
        """Sets the widget up as referencing the parameter"""
        # TODO Check if we can use `id`
        if not reference:
            return
        inputWidget = self._findWidgetFor(reference)
        if inputWidget:
            inputWidget.addReferencing(pipelineParameter)

    def removeReferencing(self, reference: Reference, pipelineParameter: PipelineParameter):
        """Forward to the appropriate parameter"""
        if not reference:
            return
        inputWidget = self._findWidgetFor(reference)
        if inputWidget:
            inputWidget.removeReferencing(pipelineParameter)

    def _findWidgetFor(self, reference: Reference) -> Optional[PipelineInputParameterWidget]:
        for widget in self._parameterWidgets:
            if reference == widget.reference:
                return widget
        return None

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

    def _addParameter(self, name=None, type_= type(None)) -> None:
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

