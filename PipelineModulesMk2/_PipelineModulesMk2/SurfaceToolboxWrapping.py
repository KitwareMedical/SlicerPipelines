from typing import Annotated

import slicer
from slicer.parameterNodeWrapper import (
    Minimum,
)
from MRMLCorePython import vtkMRMLModelNode

from PipelineCreatorMk2 import slicerPipelineMk2
from SurfaceToolbox import SurfaceToolboxLogic


def _surfaceToolboxRun(mesh: vtkMRMLModelNode,
                       operation: str,
                       params: dict[str, str]):
    outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    parameterNode = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLScriptedModuleNode")
    try:
        logic = SurfaceToolboxLogic()
        logic.setDefaultParameters(parameterNode)

        parameterNode.SetNodeReferenceID("inputModel", mesh.GetID())
        parameterNode.SetNodeReferenceID("outputModel", outputModel.GetID())
        parameterNode.SetParameter(operation, "true")
        for key, value in params.items():
            parameterNode.SetParameter(key, value)

        logic.applyFilters(parameterNode)
        return outputModel
    finally:
        slicer.mrmlScene.RemoveNode(parameterNode)


@slicerPipelineMk2(name="SurfaceToolbox.ScaleMesh", dependencies=["SurfaceToolbox"], categories=["SurfaceToolbox", "Model Operations"])
def scaleMesh(mesh: vtkMRMLModelNode,
              scaleX: Annotated[float, Minimum(0)],
              scaleY: Annotated[float, Minimum(0)],
              scaleZ: Annotated[float, Minimum(0)]) -> vtkMRMLModelNode:

    return _surfaceToolboxRun(mesh, "scale", {
        "scaleX": str(scaleX),
        "scaleY": str(scaleY),
        "scaleZ": str(scaleZ),
    })


@slicerPipelineMk2(name="SurfaceToolbox.TranslateMesh", dependencies=["SurfaceToolbox"], categories=["SurfaceToolbox", "Model Operations"])
def translateMesh(mesh: vtkMRMLModelNode,
                  translateX: float,
                  translateY: float,
                  translateZ: float) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "translate", {
        "translateX": str(translateX),
        "translateY": str(translateY),
        "translateZ": str(translateZ),
    })


@slicerPipelineMk2(name="SurfaceToolbox.Mirror", dependencies=["SurfaceToolbox"], categories=["SurfaceToolbox", "Model Operations"])
def mirrorMesh(mesh: vtkMRMLModelNode,
               mirrorX: bool,
               mirrorY: bool,
               mirrorZ: bool) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "mirror", {
        "mirrorX": str(mirrorX),
        "mirrorY": str(mirrorY),
        "mirrorZ": str(mirrorZ),
    })
