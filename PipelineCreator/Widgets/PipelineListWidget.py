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

from Widgets.ReferenceComboBox import Reference
from Widgets.PipelineStepWidget import PipelineStepWidget
from Widgets.PipelineInputWidget import PipelineInputWidget
from Widgets.PipelineOutputWidget import PipelineOutputWidget


__all__ = ["PipelineListWidget"]


class PipelineListWidget(qt.QWidget):
    """Defines the Interface for assembling a pipeline, consists of one PipelineInputWidget, one
    PipelineStepWidget per step and one PipelineOutputWidget. Each of these widgets has its own
    implementation of a Parameter. The parameters are fixed for a step, but they are determined
    by the user for the inputs and outputs.
    """
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
