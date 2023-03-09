import dataclasses
import typing
from typing import Optional

import ctk
import networkx as nx
import qt

import slicer

from .SelectPipelinePopUp import SelectPipelinePopUp

from slicer.parameterNodeWrapper import (
    createGui,
    createGuiConnector,
    findFirstAnnotation,
    isParameterPack,
    splitAnnotations,
    unannotatedType,

    Default,
)

from _PipelineCreator.PipelineRegistrar import PipelineRegistrar, PipelineInfo


__all__ = ["PipelineListWidget"]


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
        self.referenceWidget.currentIndexChanged.connect(self._emitValueChanged)

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

@dataclasses.dataclass
class PipelineStepParameterWidgets:
    """
    This widget represents a single parameter of a pipeline step.
    These parameters will always have a fixed name, and can either be a fixed
    value or a Reference to a stepOutput of a previous step. Note that MRML node
    values cannot be fixed.

    In reality, this class is a just a convenient view onto existing widgets, which
    helps with grouping and organization in code.

    This duck type matches PipelineOutputParameterWidget.
    """

    nameWidget: qt.QLabel
    fixedCheckBox: qt.QCheckBox
    referenceWidget: ReferenceComboBox
    fixedValueWidget: qt.QWidget

    @property
    def name(self) -> str:
        return self.nameWidget.text

    @property
    def fixed(self) -> bool:
        return self.fixedCheckBox.checked
    
    @property
    def type(self) -> type:
        return self.referenceWidget.paramType

    @property
    def currentReference(self) -> Reference:
        return self.referenceWidget.currentReference

    def computeFixedValue(self) -> typing.Any:
        # to get a generic value from a generic widget, make a GUI connector!
        if not hasattr(self, "_connector"):
            self._connector = createGuiConnector(self.fixedValueWidget, self.type)
        return self._connector.read()


class PipelineStepWidget(qt.QWidget):
    """
    This widget represents a single step in the pipeline that is not the overall input
    or overall output.
    
    This duck type matches the stepOutputs property of the PipelineInputWidget and the
    inputs property of PipelineOutputWidget.
    """
    requestedMoveUp = qt.Signal()
    requestedMoveDown = qt.Signal()
    requestedDelete = qt.Signal()

    def __init__(self, titleText, stepNum, info: PipelineInfo, parent=None) -> None:
        super().__init__(parent)

        self.stepInfo: PipelineInfo = info
        self._stepNumber = stepNum

        self._mainLayout = qt.QVBoxLayout(self)

        self._collapsibleButton = ctk.ctkCollapsibleButton()
        self._collapsibleButton.setProperty("PipelineStepCollapsible", True)
        self._mainLayout.addWidget(self._collapsibleButton)

        self._collapsibleButton.setLayout(qt.QVBoxLayout())
        self._collapsibleButton.setText(titleText)
        self._collapsibleButton.collapsed = False

        # up, down, delete buttons
        moveLayout = qt.QHBoxLayout()
        self._collapsibleButton.layout().addLayout(moveLayout)
        self._upButton = qt.QPushButton("↑")
        self._downButton = qt.QPushButton("↓")
        self._deleteButton = qt.QPushButton(qt.QIcon(":/Icons/MarkupsDelete.png"), "")
        upSizePolicy = self._upButton.sizePolicy
        upSizePolicy.setVerticalPolicy(qt.QSizePolicy.Expanding)
        self._upButton.setSizePolicy(upSizePolicy)
        downSizePolicy = self._downButton.sizePolicy
        downSizePolicy.setVerticalPolicy(qt.QSizePolicy.Expanding)
        self._downButton.setSizePolicy(downSizePolicy)

        self._upButton.clicked.connect(lambda: self.requestedMoveUp.emit())
        self._downButton.clicked.connect(lambda: self.requestedMoveDown.emit())
        self._deleteButton.clicked.connect(lambda: self.requestedDelete.emit())

        moveLayout.addWidget(self._upButton)
        moveLayout.addWidget(self._downButton)
        moveLayout.addWidget(self._deleteButton)

        # pipeline stuff
        self._collapsibleButton.layout().addWidget(qt.QLabel("Inputs"))
        self._setupParameterWidgets()
        self._collapsibleButton.layout().addWidget(qt.QLabel("Outputs"))
        self._setupReturnWidgets()

    @property
    def inputs(self) -> list[PipelineStepParameterWidgets]:
        return self._parameterWidgets

    @property
    def stepOutputs(self) -> list[Reference]:
        """
        The intermediate output values for this step.
        """
        returnType = unannotatedType(self.stepInfo.returnType)
        outputs = [Reference(self, 0, self.stepNumber, self.stepInfo.name, "return", returnType)]
        if isParameterPack(returnType):
            outputs += [
                Reference(self, index + 1, self.stepNumber, self.stepInfo.name, f"return.{paramName}", unannotatedType(paramInfo.unalteredType))
                for index, (paramName, paramInfo) in enumerate(returnType.allParameters.items())
            ]
        return outputs

    @property
    def stepNumber(self) -> int:
        return self._stepNumber

    @stepNumber.setter
    def stepNumber(self, num: int) -> None:
        self._stepNumber = num
        self._collapsibleButton.text = f"Step {self._stepNumber} - {self.stepInfo.name}"

    def updateInputReferences(self, inputReferences) -> None:
        for referenceCombobox in self._inputReferences:
            referenceCombobox.references = inputReferences

    def _setupFixedVsRefConnection(self, checkBox, refComboBox, fixedValueWidget) -> None:
        def chooseFixedOrRef(checkBox, refComboBox, fixedValueWidget):
            refComboBox.visible = not checkBox.checked
            fixedValueWidget.visible = checkBox.checked
        checkBox.stateChanged.connect(
                lambda: chooseFixedOrRef(checkBox, refComboBox, fixedValueWidget))

    def _setupParameterWidgets(self) -> None:
        grid = qt.QGridLayout()
        grid.setContentsMargins(15, 0, 0, 0)
        grid.setColumnStretch(1, 1)
        self._collapsibleButton.layout().addLayout(grid)

        self._inputReferences = []
        self._parameterWidgets = []
        for index, (paramName, paramType) in enumerate(self.stepInfo.parameters.items()):
            unannotatedParamType = unannotatedType(paramType)
            nameLabel = qt.QLabel(paramName)

            referenceComboBox = ReferenceComboBox(paramType)
            self._inputReferences.append(referenceComboBox)
            refSizePolicy = referenceComboBox.sizePolicy
            refSizePolicy.setRetainSizeWhenHidden(True)
            referenceComboBox.setSizePolicy(refSizePolicy)

            grid.addWidget(nameLabel, index, 0)
            grid.addWidget(referenceComboBox, index, 1)

            fixedCheckBox = qt.QCheckBox("Fixed")
            fixedCheckBox.checked = True
            grid.addWidget(fixedCheckBox, index, 2)

            if not (isinstance(unannotatedParamType, type) and issubclass(unannotatedParamType, slicer.vtkMRMLNode)):
                fixedValueWidget = createGui(paramType)
                # use a connector to set things like Decimals, Minimum, etc, then use to set the default
                connector = createGuiConnector(fixedValueWidget, paramType)
                default = findFirstAnnotation(splitAnnotations(paramType)[1], Default)
                if default is not None:
                    connector.write(default.value)
                fixedValSizePolicy = fixedValueWidget.sizePolicy
                fixedValSizePolicy.setRetainSizeWhenHidden(True)
                fixedValueWidget.setSizePolicy(fixedValSizePolicy)

                self._setupFixedVsRefConnection(fixedCheckBox, referenceComboBox, fixedValueWidget)
                referenceComboBox.hide()

                grid.addWidget(fixedValueWidget, index, 1)
                grid.addWidget(fixedCheckBox, index, 2)
                self._parameterWidgets.append(PipelineStepParameterWidgets(nameLabel, fixedCheckBox, referenceComboBox, fixedValueWidget))
            else:
                # hide checkbox because it can't be fixed
                fixedCheckBox.checked = False
                fixedCheckBox.hide()
                self._parameterWidgets.append(PipelineStepParameterWidgets(nameLabel, fixedCheckBox, referenceComboBox, None))

    def _setupReturnWidgets(self) -> None:
        grid = qt.QGridLayout()
        grid.setContentsMargins(15, 0, 0, 0)
        grid.setColumnStretch(0, 1)
        self._collapsibleButton.layout().addLayout(grid)

        unannotatedReturnType = unannotatedType(self.stepInfo.returnType)

        grid.addWidget(qt.QLabel("return"), 0, 0)
        grid.addWidget(qt.QLabel(f"({unannotatedReturnType.__name__})"), 0, 1)

        if isParameterPack(unannotatedReturnType):
             for index, (paramName, paramInfo) in enumerate(unannotatedReturnType.allParameters.items()):
                 grid.addWidget(qt.QLabel(f"return.{paramName}"), index + 1, 0)
                 grid.addWidget(qt.QLabel(f"({unannotatedType(paramInfo.unalteredType).__name__})"), index + 1, 1)


class PipelineListWidget(qt.QWidget):
    def __init__(self, registrar: PipelineRegistrar, parent = None):
        super().__init__(parent)

        self.registrar = registrar

        self.setLayout(qt.QVBoxLayout())
        self.styleSheet = '[PipelineStepCollapsible="true"]{background-color: palette(dark)}'
        self._inputsWidget = PipelineInputWidget(0, "Inputs", "inputValue", sorted(list(registrar.pipelinedTypes), key=lambda t: t.__name__.lower()))
        self._inputsWidget.valueChanged.connect(self._updateSteps)

        self._stepsContainer = qt.QWidget()
        self._stepsContainer.setLayout(qt.QVBoxLayout())

        self._addStepButton = qt.QPushButton("Add Step")
        self._addStepButton.clicked.connect(self._insertPipelineStep)

        self._outputsWidget = PipelineOutputWidget(1, "Outputs", "outputValue")
        self._outputsWidget.valueChanged.connect(self._updateSteps)

        self._updateSteps()

        self.layout().addWidget(self._inputsWidget)
        self.layout().addWidget(self._stepsContainer)
        self.layout().addWidget(self._addStepButton)
        self.layout().addWidget(self._outputsWidget)

    @property
    def _stepWidgets(self) -> list[PipelineStepWidget]:
        layout = self._stepsContainer.layout()
        return [layout.itemAt(i).widget() for i in range(layout.count())]

    def computePipeline(self) -> nx.DiGraph:
        # overall input nodes
        pipeline = nx.DiGraph()
        for index, reference in enumerate(self._inputsWidget.stepOutputs):
            pipeline.add_node((reference.step, None, reference.itemName), datatype=unannotatedType(reference.type), position=index)

        # middle nodes
        for stepWidget in self._stepWidgets:
            # input side
            for desc in stepWidget.inputs:
                pipeline.add_node((stepWidget.stepNumber, stepWidget.stepInfo.name, desc.name), datatype=unannotatedType(desc.type))
                if desc.fixed:
                    pipeline.nodes[(stepWidget.stepNumber, stepWidget.stepInfo.name, desc.name)]["fixed_value"] = desc.computeFixedValue()
                else:
                    if desc.currentReference is None:
                        raise ValueError("Cannot build a pipeline with an unset reference."
                                         f" See step {stepWidget.stepNumber} - {desc.name}")
                    pipeline.add_edge((desc.currentReference.step, desc.currentReference.stepName, desc.currentReference.itemName),
                                      (stepWidget.stepNumber, stepWidget.stepInfo.name, desc.name))

            # output side
            for reference in stepWidget.stepOutputs:
                pipeline.add_node((reference.step, reference.stepName, reference.itemName), datatype=unannotatedType(reference.type))

        # overall output nodes
        for index, desc in enumerate(self._outputsWidget.inputs):
            if desc.currentReference is None:
                raise ValueError("Cannot build a pipeline with an unset reference."
                                 f" See output {desc.name}")
            pipeline.add_node((self._outputsWidget.stepNumber, None, desc.name), datatype=unannotatedType(desc.currentReference.type), position=index)
            pipeline.add_edge((desc.currentReference.step, desc.currentReference.stepName, desc.currentReference.itemName),
                              (self._outputsWidget.stepNumber, None, desc.name))

        return pipeline

    def _computeStepOutputs(self) -> list[Reference]:
        refs = self._inputsWidget.stepOutputs
        layout = self._stepsContainer.layout()
        for i in range(layout.count()):
            refs += layout.itemAt(i).widget().stepOutputs

        # The overall outputs don't have step outputs since nothing is below it
        return refs

    def _updateSteps(self) -> None:
        layout = self._stepsContainer.layout()
        numRows = layout.count()

        for stepNum in range(1, numRows + 1):
            stepWidget = layout.itemAt(stepNum - 1).widget()
            stepWidget.stepNumber = stepNum

        newOutputs = self._computeStepOutputs()

        for stepNum in range(1, numRows + 1):
            stepWidget = layout.itemAt(stepNum - 1).widget()
            stepWidget.updateInputReferences([r for r in newOutputs if r.step < stepNum])

        self._outputsWidget.stepNumber = numRows + 1
        self._outputsWidget.updateInputReferences(newOutputs)

    def _insertPipelineStep(self) -> None:
        popUp = SelectPipelinePopUp(self.registrar.registeredPipelines, parent=slicer.util.mainWindow())
        popUp.accepted.connect(lambda: self._onInsertPipelineStepAccepted(popUp))
        popUp.rejected.connect(lambda: popUp.deleteLater())
        popUp.open()

    def _onInsertPipelineStepAccepted(self, popUp) -> None:
        layout = self._stepsContainer.layout()
        stepWidget = PipelineStepWidget("Temp - will be filled by _updateSteps", layout.count() + 1, popUp.selectedPipeline)
        layout.addWidget(stepWidget)
        stepWidget.requestedMoveUp.connect(lambda: self._moveStep(stepWidget, -1))
        stepWidget.requestedMoveDown.connect(lambda: self._moveStep(stepWidget, 1))
        stepWidget.requestedDelete.connect(lambda: self._deleteStep(stepWidget))
        self._updateSteps()
        popUp.deleteLater()

    def _moveStep(self, stepWidget, movement) -> None:
        layout = self._stepsContainer.layout()
        widgetIndex = layout.indexOf(stepWidget)

        if widgetIndex == -1:
            print("Error: could not find widget to move")
            return

        if 0 <= widgetIndex + movement < layout.count():
            stepWidget.hide()
            layout.removeWidget(stepWidget)
            layout.insertWidget(widgetIndex + movement, stepWidget)
            stepWidget.show()
            self._updateSteps()

    def _deleteStep(self, stepWidget) -> None:
        stepWidget.hide()
        self._stepsContainer.layout().removeWidget(stepWidget)
        self._updateSteps()
        stepWidget.deleteLater()
