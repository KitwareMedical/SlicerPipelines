import os
import pathlib
import typing
from typing import Annotated, Optional

try:
    import networkx as nx
except ImportError:
    import slicer
    slicer.util.pip_install("networkx")
    import networkx as nx

import qt

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    Default,
    parameterNodeWrapper,
    parameterPack,
)

from _PipelineCreatorMk2.PipelineRegistrar import PipelineRegistrar, PipelineInfo
from _PipelineCreatorMk2 import PipelineCreation
from _PipelineCreatorMk2.PipelineCreation.util import printPipeline

from Widgets.PipelineListWidget import PipelineListWidget
from Widgets.SelectPipelinePopUp import SelectPipelinePopUp

__all__ = [
    "PipelineRegistrar", # repackage to public because PipelineListWidget uses it
    "PipelineCreatorMk2",
    "PipelineCreatorMk2Widget",
    "PipelineCreatorMk2Logic",
    "singletonRegisterPipelineFunction",
    "slicerPipelineMk2",
]


#
# PipelineCreatorMk2
#

class PipelineCreatorMk2(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        # TODO: make this more human readable by adding spaces
        self.parent.title = "PipelineCreatorMk2"
        self.parent.categories = ["Pipelines"]
        self.parent.dependencies = []
        self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#PipelineCreatorMk2">module documentation</a>.
"""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""


#
# PipelineCreatorMk2ParameterNode
#

def _defaultIcon():
    # this will not change, but it can't be queried until this module is loaded
    return pathlib.Path(os.path.join(
        os.path.dirname(slicer.util.modulePath(PipelineCreatorMk2.__name__)),
        'Resources',
        'Icons',
        'PipelineCreatorMk2_template_icon.png')
    )


@parameterNodeWrapper
class PipelineCreatorMk2ParameterNode:
    """
    The parameters needed by module.
    """
    pipelineName: str
    outputDirectory: pathlib.Path
    icon: Annotated[pathlib.Path, Default(generator=_defaultIcon)]


#
# PipelineCreatorMk2Widget
#

class PipelineCreatorMk2Widget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        # needed for parameter node observation
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(
            self.resourcePath('UI/PipelineCreatorMk2.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = PipelineCreatorMk2Logic()

        # Finish adding the widgets
        self.ui.StepsContainerWidget.setLayout(qt.QVBoxLayout())
        self.ui.PipelineListWidget = PipelineListWidget(self.logic.registrar)
        self.ui.StepsContainerWidget.layout().addWidget(self.ui.PipelineListWidget)

        # Connections
        self.ui.GeneratePipelineButton.clicked.connect(self.onGeneratePipeline)

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self) -> None:
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None

    def onSceneStartClose(self, caller, event) -> None:
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode: Optional[PipelineCreatorMk2ParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)

    def onGeneratePipeline(self):
        try:
            self.logic.createPipeline(
                self._parameterNode.pipelineName,
                self._parameterNode.outputDirectory,
                self.ui.PipelineListWidget.computePipeline(),
                self._parameterNode.icon)
            msgbox = qt.QMessageBox()
            msgbox.setWindowTitle("SUCCESS")
            msgbox.setText(f"Successfully created Pipeline '{self._parameterNode.pipelineName}' at '{self._parameterNode.outputDirectory}'!")
            msgbox.exec()
        except Exception as e:
            msgbox = qt.QMessageBox()
            msgbox.setWindowTitle("ERROR")
            msgbox.setText(f"Failed to create Pipeline:\n  {str(e)}")
            msgbox.exec()
            raise

#
# PipelineCreatorMk2Logic
#

class PipelineCreatorMk2Logic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    _singletonRegistrar: PipelineRegistrar = PipelineRegistrar()

    def __init__(self, useSingleton=True) -> None:
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

        self.isSingletonParameterNode = useSingleton
        if useSingleton:
            self._registrar = self._singletonRegistrar
        else:
            self._registrar: PipelineRegistrar = PipelineRegistrar()

    def getParameterNode(self):
        return PipelineCreatorMk2ParameterNode(super().getParameterNode())

    #################################################################
    #
    # Functions related to registering existing pipelines
    #
    #################################################################
    @staticmethod
    def validatePipelineFunction(function) -> None:
        PipelineRegistrar.validatePipelineFunction(function)

    @property
    def registeredPipelines(self) -> dict[str, PipelineInfo]:
        return self._registrar.registeredPipelines

    @property
    def registrar(self) -> PipelineRegistrar:
        return self._registrar

    def isRegistered(self, pipelineName: str) -> bool:
        return self._registrar.isRegistered(pipelineName)

    def registerPipeline(self, name: str, function, dependencies, categories=None) -> None:
        self._registrar.registerPipeline(name, function, dependencies, categories)

    #################################################################
    #
    # Functions related to creating new pipelines
    #
    #################################################################
    def fillInDataTypes(self, pipeline: nx.DiGraph) -> None:
        PipelineCreation.fillInDataTypes(pipeline, self.registeredPipelines)

    def createPipeline(self,
                       name: str,
                       outputDirectory: pathlib.Path,
                       pipeline: nx.DiGraph,
                       icon=None) -> None:
        icon = icon or _defaultIcon()

        PipelineCreation.createPipeline(
            name=name,
            outputDirectory=outputDirectory,
            pipeline=pipeline,
            registeredPipelines=self.registeredPipelines,
            icon=icon)

#
# Free functions
#


def _callAfterAllTheseModulesLoaded(callback, modules):
    # if all modules are loaded
    if not set(modules).difference(set(slicer.app.moduleManager().modulesNames())):
        callback()
    else:
        def callbackWrapper():
            if not set(modules).difference(set(slicer.app.moduleManager().modulesNames())):
                callback()
                slicer.app.moduleManager().moduleLoaded.disconnect(callbackWrapper)
        slicer.app.moduleManager().moduleLoaded.connect(callbackWrapper)


def singletonRegisterPipelineFunction(pipelineName, function, dependencies, categories):
    """
    This method will handle correctly registering the module regardless of if
    the pipeline creator has already been loaded into slicer when it is called
    """
    def registerPipeline():
        PipelineCreatorMk2Logic().registerPipeline(
            pipelineName, function, dependencies, categories)
    _callAfterAllTheseModulesLoaded(registerPipeline, dependencies)


def slicerPipelineMk2(name=None, dependencies=None, categories=None):
    """
    Class decorator to automatically register a function with the PipelineCreatorMk2
    """

    def Inner(func):
        singletonRegisterPipelineFunction(name, func, dependencies or [], categories or [])

        return func
    return Inner
