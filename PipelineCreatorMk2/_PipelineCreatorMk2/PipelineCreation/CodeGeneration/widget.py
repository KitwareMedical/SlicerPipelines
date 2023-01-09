import textwrap

import networkx as nx

from MRMLCorePython import vtkMRMLNode

from slicer.parameterNodeWrapper import unannotatedType

from _PipelineCreatorMk2.PipelineCreation.CodeGeneration.util import CodePiece

from _PipelineCreatorMk2.PipelineCreation.util import (
    getStep,
)
from _PipelineCreatorMk2.PipelineCreation.CodeGeneration.util import (
    CodePiece,
    cleanupImports,
    importCodeForTypes,
    typeAsCode,
)

def createParameterPack(name: str, step: int, pipeline: nx.DiGraph, tab: str=" "*4):
    # the overall input will be put in a parameterNodeWrapper
    params, _ = getStep(step, pipeline)

    imports = f'''
from slicer.parameterNodeWrapper import parameterPack
{importCodeForTypes(params, pipeline)}
'''
    code = f'''
@parameterPack
class {name}:'''.lstrip()

    for param in params:
        code += f"\n{tab}{param[2]}: {typeAsCode(pipeline.nodes[param]['datatype'])}"

    return CodePiece(imports=cleanupImports(imports), code=code)


def _createOnRunFunction(logicRunMethodName: str, pipeline: nx.DiGraph, tab: str=" "*4):
    params, _ = getStep(0, pipeline)
    args = [f"{p[2]}=self._parameterNode.inputs.{p[2]}" for p in params]
    argsCode = textwrap.indent(",\n".join(args), tab * 2)

    outputs, _ = getStep(-1, pipeline)
    outputNames = [f"_ret_{outputNode[2]}" for outputNode in outputs]
    outputNodeNames = [f"_ret_{outputNode[2]}" for outputNode in outputs if issubclass(unannotatedType(pipeline.nodes[outputNode]["datatype"]), vtkMRMLNode)]

    outputFillCode = []
    for outputNode in outputs:
        if not issubclass(pipeline.nodes[outputNode]['datatype'], vtkMRMLNode):
            outputFillCode.append(f"self._parameterNode.outputs.{outputNode[2]} = _ret_{outputNode[2]}")
        else:
            outputFillCode.append(f"self._parameterNode.outputs.{outputNode[2]}.CopyContent(_ret_{outputNode[2]})")
    outputFillCode = "\n".join(outputFillCode)

    outputMRMLNodeRemovalCode = "\n".join(f"slicer.mrmlScene.RemoveNode({name})" for name in outputNodeNames)

    code = f'''
def _onRun(self):
{tab}{", ".join(outputNames)} = self.logic.{logicRunMethodName}(
{argsCode})

{textwrap.indent(outputFillCode, tab)}

{textwrap.indent(outputMRMLNodeRemovalCode, tab)}'''.strip()
    return code

def createWidget(name: str,
                 logicClassName: str,
                 logicRunMethodName: str,
                 pipeline: nx.DiGraph,
                 tab: str=" "*4) -> CodePiece:

    inputsCode = createParameterPack(f"{name}Inputs", 0, pipeline, tab)
    outputsCode = createParameterPack(f"{name}Outputs", -1, pipeline, tab)
    onRunFunc = _createOnRunFunction(logicRunMethodName, pipeline)

    # imports
    imports = inputsCode.imports + "\n"
    imports = outputsCode.imports + "\n"
    imports += "from typing import Optional\n"
    imports += "import qt\n"
    imports += "import slicer\n"
    imports += "from slicer.ScriptedLoadableModule import ScriptedLoadableModuleWidget\n"
    imports += "from slicer.util import VTKObservationMixin\n"
    imports += "from slicer.parameterNodeWrapper import createGui\n"
    imports += "from slicer.parameterNodeWrapper import parameterNodeWrapper\n"

    # code
    code = f'''
#
# {name}Inputs
#

{inputsCode.code}


#
# {name}Outputs
#

{outputsCode.code}


#
# {name}ParameterNode
#

@parameterNodeWrapper
class {name}ParameterNode:
    inputs: {name}Inputs
    outputs: {name}Outputs


#
# {name}Widget
#

class {name}Widget(ScriptedLoadableModuleWidget, VTKObservationMixin):
{tab}def __init__(self, parent):
{tab}{tab}ScriptedLoadableModuleWidget.__init__(self, parent)
{tab}{tab}self.logic = None
{tab}{tab}self._parameterNode = None
{tab}{tab}self._parameterNodeGuiTag = None

{tab}def setup(self):
{tab}{tab}ScriptedLoadableModuleWidget.setup(self)
{tab}{tab}self.logic = {logicClassName}()
{tab}{tab}self.paramWidget = createGui({name}ParameterNode)
{tab}{tab}self.paramWidget.setMRMLScene(slicer.mrmlScene)
{tab}{tab}self.runButton = qt.QPushButton("Run")

{tab}{tab}self.layout.addWidget(self.paramWidget)
{tab}{tab}self.layout.addWidget(self.runButton)
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

{tab}{tab}self.setParameterNode({name}ParameterNode(self.logic.getParameterNode()))

{tab}def setParameterNode(self, inputParameterNode: Optional[{name}ParameterNode]) -> None:
{tab}{tab}"""
{tab}{tab}Set and observe parameter node.
{tab}{tab}Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
{tab}{tab}"""

{tab}{tab}if self._parameterNode:
{tab}{tab}{tab}self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
{tab}{tab}self._parameterNode = inputParameterNode
{tab}{tab}if self._parameterNode:
{tab}{tab}{tab}self._parameterNodeGuiTag = self._parameterNode.connectGui(self.paramWidget)

{textwrap.indent(onRunFunc, tab)}
'''.lstrip()

    return CodePiece(imports=cleanupImports(imports), code=code)
