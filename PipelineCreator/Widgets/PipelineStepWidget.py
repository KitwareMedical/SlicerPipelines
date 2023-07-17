import dataclasses
import typing

import qt
import slicer
import ctk

from slicer.parameterNodeWrapper import (
    createGui,
    createGuiConnector,
    findFirstAnnotation,
    isParameterPack,
    splitAnnotations,
    unannotatedType,
    Default
)
from _PipelineCreator.PipelineRegistrar import PipelineInfo
from Widgets.ReferenceComboBox import Reference, ReferenceComboBox

@dataclasses.dataclass
class PipelineStepParameterWidget(qt.QWidget):
    """
    This widget represents a single parameter of a pipeline step.
    These parameters will always have a fixed name, and can either be a fixed
    value or a Reference to a stepOutput of a previous step. Note that MRML node
    values cannot be fixed.

    In reality, this class is a just a convenient view onto existing widgets, which
    helps with grouping and organization in code.

    This duck type matches PipelineOutputParameterWidget.
    """

    nameWidget: qt.QLabel = None
    fixedCheckBox: qt.QCheckBox = None
    referenceComboBox: ReferenceComboBox = None
    fixedValueWidget: qt.QWidget = None

    def __init__(self, grid: qt.QGridLayout, index : int, paramName: str, paramType: type, parent= None):
            super().__init__(parent)
            unannotatedParamType = unannotatedType(paramType)
            self.nameLabel = qt.QLabel(paramName)

            self.referenceComboBox = ReferenceComboBox(paramType)
            refSizePolicy = self.referenceComboBox.sizePolicy
            refSizePolicy.setRetainSizeWhenHidden(True)
            self.referenceComboBox.setSizePolicy(refSizePolicy)

            grid.addWidget(self.nameLabel, index, 0)
            grid.addWidget(self.referenceComboBox, index, 1)

            self.fixedCheckBox = qt.QCheckBox("Fixed")
            self.fixedCheckBox.checked = True
            grid.addWidget(self.fixedCheckBox, index, 2)

            if not (isinstance(unannotatedParamType, type) and issubclass(unannotatedParamType, slicer.vtkMRMLNode)):
                self.fixedValueWidget = createGui(paramType)
                # use a connector to set things like Decimals, Minimum, etc, then use to set the default
                connector = createGuiConnector(self.fixedValueWidget, paramType)
                default = findFirstAnnotation(splitAnnotations(paramType)[1], Default)
                if default is not None:
                    connector.write(default.value)
                fixedValSizePolicy = self.fixedValueWidget.sizePolicy
                fixedValSizePolicy.setRetainSizeWhenHidden(True)
                self.fixedValueWidget.setSizePolicy(fixedValSizePolicy)

                self.fixedCheckBox.stateChanged.connect(self._onFixedChecked)
                self.referenceComboBox.hide()

                grid.addWidget(self.fixedValueWidget, index, 1)
                grid.addWidget(self.fixedCheckBox, index, 2)
            else:
                # hide checkbox because it can't be fixed
                self.fixedCheckBox.checked = False
                self.fixedCheckBox.hide()

    def _onFixedChecked(self):
        self.referenceComboBox.visible = not self.fixedCheckBox.checked
        self.fixedValueWidget.visible = self.fixedCheckBox.checked

    @property
    def name(self) -> str:
        return self.nameWidget.text

    @property
    def fixed(self) -> bool:
        return self.fixedCheckBox.checked

    @property
    def type(self) -> type:
        return self.referenceComboBox.paramType

    @property
    def currentReference(self) -> Reference:
        return self.referenceComboBox.currentReference

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
    def inputs(self) -> list[PipelineStepParameterWidget]:
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

    def _setupParameterWidgets(self) -> None:
        grid = qt.QGridLayout()

        # TODO maybe refactor to VBox and HBox layouts
        grid.setContentsMargins(15, 0, 0, 0)
        grid.setColumnStretch(1, 1)
        self._collapsibleButton.layout().addLayout(grid)

        self._inputReferences = []
        self._parameterWidgets = []
        for index, (paramName, paramType) in enumerate(self.stepInfo.parameters.items()):
            widget = PipelineStepParameterWidget(grid, index, paramName, paramType)
            self._parameterWidgets.append(widget)
            self._inputReferences.append(widget.referenceComboBox)

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
