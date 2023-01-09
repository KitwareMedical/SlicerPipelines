import os

import qt
import slicer


class SelectPipelinePopUp(qt.QDialog):
    def __init__(self, registeredPipelines, parent=None):
        qt.QDialog.__init__(self, parent)

        self._registeredPipelines = registeredPipelines
        self._selectedPipeline = None

        self._mainLayout = qt.QVBoxLayout(self)

        self._uiWidget = slicer.util.loadUI(
            os.path.join(
                os.path.dirname(slicer.util.modulePath("PipelineCreatorMk2")),
                "Resources",
                "UI",
                "SelectPipelinePopUp.ui")
        )
        self._mainLayout.addWidget(self._uiWidget)
        self.ui = slicer.util.childWidgetVariables(self._uiWidget)
        self.ui.ButtonBox.accepted.connect(self.accept)
        self.ui.ButtonBox.rejected.connect(self.reject)

        for pipelineName in self._registeredPipelines.keys():
            self.ui.PipelineList.addItem(pipelineName)

        # delete start
        self.ui.PipelineList.setDragDropMode(qt.QAbstractItemView.InternalMove)
        # delete end

        self.ui.PipelineList.currentItemChanged.connect(self._updateOutput)

        # double click same as accept
        self.ui.PipelineList.itemDoubleClicked.connect(self._updateAndAccept)

    def _updateOutput(self):
        listItem = self.ui.PipelineList.currentItem()
        self.ui.ButtonBox.button(self.ui.ButtonBox.Ok).enabled = bool(listItem)
        if listItem:
            self._selectedPipeline = self._registeredPipelines[listItem.text()]
        else:
            self._selectedPipeline = None

    def _updateAndAccept(self):
        self._updateOutput()
        self.accept()

    @property
    def selectedPipeline(self):
        return self._selectedPipeline
