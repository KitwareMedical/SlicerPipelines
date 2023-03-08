import textwrap

import networkx as nx

from _PipelineCreator.PipelineCreation.CodeGeneration.util import CodePiece

from _PipelineCreator.PipelineCreation.util import (
    getStep,
)
from _PipelineCreator.PipelineCreation.CodeGeneration.util import (
    CodePiece,
    cleanupImports,
)


def _createOnRunFunction(logicRunMethodName: str,
                         pipeline: nx.DiGraph,
                         parameterNodeOutputsPackName: str,
                         tab: str):
    params, _ = getStep(0, pipeline)
    args = [f"{p[2]}=self._parameterNode.inputs.{p[2]}" for p in params]
    argsCode = textwrap.indent(",\n".join(args), tab * 2)

    code = f'''
def _onRun(self):
{tab}outputValue = self.logic.{logicRunMethodName}(
{argsCode},
{tab}{tab}progress_callback=self.progressBar.getProgressCallback())

{tab}# Copy the output. Use CopyContent for nodes and do a normal copy for non-nodes.
{tab}# For parameterPacks, need to recurse into them though so CopyContent can be used for
{tab}# node members.
{tab}if isinstance(outputValue, {parameterNodeOutputsPackName}):
{tab}{tab}self._copyParameterPack(outputValue, self._parameterNode.outputs)
{tab}elif isParameterPack(outputValue):
{tab}{tab}# A parameter pack, but not the output one
{tab}{tab}paramName = next(iter(self._parameterNode.outputs.allParameters.keys()))
{tab}{tab}self._copyParameterPack(outputValue, self._parameterNode.outputs.getValue(paramName))
{tab}elif isinstance(outputValue, vtkMRMLNode):
{tab}{tab}# if the output is not a parameter pack, there is only one output
{tab}{tab}paramName = next(iter(self._parameterNode.outputs.allParameters.keys()))
{tab}{tab}self._copyNode(outputValue, self._parameterNode.outputs.getValue(paramName))
{tab}else:
{tab}{tab}# single value that is not a node
{tab}{tab}paramName = next(iter(self._parameterNode.outputs.allParameters.keys()))
{tab}{tab}self._parameterNode.outputs.setValue(paramName, outputValue)

{tab}self._removeNodes(outputValue)
'''.strip()
    return code

def createWidget(name: str,
                 parameterNodeClassName: str,
                 parameterNodeOutputsClassName: str,
                 logicClassName: str,
                 logicRunMethodName: str,
                 pipeline: nx.DiGraph,
                 tab: str=" "*4) -> CodePiece:

    onRunFunc = _createOnRunFunction(logicRunMethodName, pipeline, parameterNodeOutputsClassName, tab)

    # imports
    imports = "\n".join([
        "from typing import Optional",
        "import qt",
        "import slicer",
        "from slicer import vtkMRMLNode",
        "from slicer.ScriptedLoadableModule import ScriptedLoadableModuleWidget",
        "from slicer.util import VTKObservationMixin",
        "from slicer.parameterNodeWrapper import createGui",
        "from slicer.parameterNodeWrapper import parameterNodeWrapper",
        "from slicer.parameterNodeWrapper import isParameterPack",
        "from Widgets.PipelineProgressBar import PipelineProgressBar",
    ]) + "\n"

    # code
    code = f'''
#
# {name}Widget
#

class {name}Widget(ScriptedLoadableModuleWidget, VTKObservationMixin):
{tab}def __init__(self, parent=None):
{tab}{tab}self.logic = None
{tab}{tab}self._parameterNode = None
{tab}{tab}self._parameterNodeGuiTag = None
{tab}{tab}ScriptedLoadableModuleWidget.__init__(self, parent)

{tab}def setup(self):
{tab}{tab}ScriptedLoadableModuleWidget.setup(self)
{tab}{tab}self.logic = {logicClassName}()
{tab}{tab}self.paramWidget = createGui({parameterNodeClassName})
{tab}{tab}self.paramWidget.setMRMLScene(slicer.mrmlScene)
{tab}{tab}self.runButton = qt.QPushButton("Run")
{tab}{tab}self.progressBar = PipelineProgressBar()

{tab}{tab}self.layout.addWidget(self.paramWidget)
{tab}{tab}self.layout.addWidget(self.runButton)
{tab}{tab}self.layout.addWidget(self.progressBar)
{tab}{tab}self.layout.addStretch()

{tab}{tab}# These connections ensure that we update parameter node when scene is closed
{tab}{tab}self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
{tab}{tab}self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

{tab}{tab}# Connect the run button
{tab}{tab}self.runButton.clicked.connect(self._onRun)

{tab}{tab}# Make sure parameter node is initialized (needed for module reload)
{tab}{tab}self.initializeParameterNode()

{tab}def cleanup(self) -> None:
{tab}{tab}"""
{tab}{tab}Called when the application closes and the module widget is destroyed.
{tab}{tab}"""
{tab}{tab}self.removeObservers()

{tab}def enter(self) -> None:
{tab}{tab}"""
{tab}{tab}Called each time the user opens this module.
{tab}{tab}"""
{tab}{tab}# Make sure parameter node exists and observed
{tab}{tab}self.initializeParameterNode()

{tab}def exit(self) -> None:
{tab}{tab}"""
{tab}{tab}Called each time the user opens a different module.
{tab}{tab}"""
{tab}{tab}# Do not react to parameter node changes (GUI will be updated when the user enters into the module)
{tab}{tab}if self._parameterNode:
{tab}{tab}{tab}self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
{tab}{tab}{tab}self._parameterNodeGuiTag = None

{tab}def onSceneStartClose(self, caller, event) -> None:
{tab}{tab}"""
{tab}{tab}Called just before the scene is closed.
{tab}{tab}"""
{tab}{tab}# Parameter node will be reset, do not use it anymore
{tab}{tab}self.setParameterNode(None)

{tab}def onSceneEndClose(self, caller, event) -> None:
{tab}{tab}"""
{tab}{tab}Called just after the scene is closed.
{tab}{tab}"""
{tab}{tab}# If this module is shown while the scene is closed then recreate a new parameter node immediately
{tab}{tab}if self.parent.isEntered:
{tab}{tab}{tab}self.initializeParameterNode()

{tab}def initializeParameterNode(self) -> None:
{tab}{tab}"""
{tab}{tab}Ensure parameter node exists and observed.
{tab}{tab}"""
{tab}{tab}# Parameter node stores all user choices in parameter values, node selections, etc.
{tab}{tab}# so that when the scene is saved and reloaded, these settings are restored.

{tab}{tab}self.setParameterNode({parameterNodeClassName}(self.logic.getParameterNode()))

{tab}def setParameterNode(self, inputParameterNode: Optional[{parameterNodeClassName}]) -> None:
{tab}{tab}"""
{tab}{tab}Set and observe parameter node.
{tab}{tab}Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
{tab}{tab}"""

{tab}{tab}if self._parameterNode:
{tab}{tab}{tab}self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
{tab}{tab}self._parameterNode = inputParameterNode
{tab}{tab}if self._parameterNode:
{tab}{tab}{tab}self._parameterNodeGuiTag = self._parameterNode.connectGui(self.paramWidget)

{tab}def _copyNode(self, src, dest):
{tab}{tab}# Clones src into dest, but keeps dest's display and storage nodes, if any
{tab}{tab}# If neither src nor dest has display nodes, the default are created
{tab}{tab}if src is not None and dest is not None:
{tab}{tab}{tab}name = dest.GetName()
{tab}{tab}{tab}if dest.IsA('vtkMRMLDisplayableNode'):
{tab}{tab}{tab}{tab}displayNodesIDs = [dest.GetNthDisplayNodeID(n) for n in range(dest.GetNumberOfDisplayNodes())]
{tab}{tab}{tab}{tab}storageNodesIDs = [dest.GetNthStorageNodeID(n) for n in range(dest.GetNumberOfStorageNodes())]

{tab}{tab}{tab}dest.Copy(src)
{tab}{tab}{tab}dest.SetName(name)

{tab}{tab}{tab}if dest.IsA('vtkMRMLDisplayableNode'):
{tab}{tab}{tab}{tab}dest.RemoveAllDisplayNodeIDs()
{tab}{tab}{tab}{tab}for n, displayNodeID in enumerate(displayNodesIDs):
{tab}{tab}{tab}{tab}{tab}dest.SetAndObserveNthDisplayNodeID(n, displayNodeID)
{tab}{tab}{tab}{tab}for n, storageNodeID in enumerate(storageNodesIDs):
{tab}{tab}{tab}{tab}{tab}dest.SetAndObserveNthStorageNodeID(n, storageNodeID)

{tab}def _copyParameterPack(self, from_, to):
{tab}{tab}for paramName in from_.allParameters:
{tab}{tab}{tab}if isinstance(from_.getValue(paramName), vtkMRMLNode):
{tab}{tab}{tab}{tab}self._copyNode(from_.getValue(paramName), to.getValue(paramName))
{tab}{tab}{tab}elif isParameterPack(from_.getValue(paramName)):
{tab}{tab}{tab}{tab}self._copyParameterPack(from_.getValue(paramName), to.getValue(paramName))
{tab}{tab}{tab}else:
{tab}{tab}{tab}{tab}to.setValue(paramName, from_.getValue(paramName))

{tab}def _removeNodes(self, item):
{tab}{tab}if isinstance(item, vtkMRMLNode):
{tab}{tab}{tab}slicer.mrmlScene.RemoveNode(item)
{tab}{tab}elif isParameterPack(item):
{tab}{tab}{tab}for paramName in item.allParameters.keys():
{tab}{tab}{tab}{tab}self._removeNodes(item.getValue(paramName))

{textwrap.indent(onRunFunc, tab)}
'''.lstrip()

    return CodePiece(imports=cleanupImports(imports), code=code)
