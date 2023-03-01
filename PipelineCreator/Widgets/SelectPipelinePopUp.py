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
                os.path.dirname(slicer.util.modulePath("PipelineCreator")),
                "Resources",
                "UI",
                "SelectPipelinePopUp.ui")
        )
        self._mainLayout.addWidget(self._uiWidget)
        self.ui = slicer.util.childWidgetVariables(self._uiWidget)
        self.ui.ButtonBox.accepted.connect(self.accept)
        self.ui.ButtonBox.rejected.connect(self.reject)

        self.ui.ButtonBox.button(qt.QDialogButtonBox.Ok).enabled = False

        for pipelineName in self._registeredPipelines.keys():
            self.ui.PipelineList.addItem(pipelineName)

        self.ui.PipelineList.currentItemChanged.connect(self._updateOutput)

        # double click same as accept
        self.ui.PipelineList.itemDoubleClicked.connect(self._updateAndAccept)

        categories = sorted(list(set(c for info in registeredPipelines.values() for c in info.categories)))
        self.ui.CategoryComboBox.addItem("All")
        for category in categories:
            self.ui.CategoryComboBox.addItem(category)
        self.ui.CategoryComboBox.currentIndexChanged.connect(self._filterByCategory)

    def _filterByCategory(self):
        self.ui.PipelineList.clear()
        for pipelineName, info in self._registeredPipelines.items():
            if self.ui.CategoryComboBox.currentText == "All" or self.ui.CategoryComboBox.currentText in info.categories:
                self.ui.PipelineList.addItem(pipelineName)


    def _updateOutput(self):
        self.ui.ButtonBox.button(qt.QDialogButtonBox.Ok).enabled = self.ui.PipelineList.currentIndex >= 0
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
