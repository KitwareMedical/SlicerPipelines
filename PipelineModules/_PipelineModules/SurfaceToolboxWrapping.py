from typing import Annotated

import slicer
from slicer.parameterNodeWrapper import (
    Decimals,
    Default,
    Minimum,
    SingleStep,
    WithinRange,
)
from slicer import vtkMRMLModelNode

from PipelineCreator import slicerPipeline
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


_surfaceToolboxDeps = ["SurfaceToolbox"]
_surfaceToolboxCats = ["SurfaceToolbox", "Model Operations"]


def formatBool(cond):
    return "true" if cond else "false"


@slicerPipeline(name="SurfaceToolbox.Clean", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def clean(mesh: vtkMRMLModelNode) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "cleaner", {})


@slicerPipeline(name="SurfaceToolbox.UniformRemesh", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def remesh(mesh: vtkMRMLModelNode,
           numPoints: Annotated[int, WithinRange(100, 100000), Default(10000)],
           subdivide: Annotated[int, WithinRange(0, 8)]) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "remesh", {
        "remeshSubdivide": str(subdivide),
        "remeshClustersK": str(numPoints / 1000),
    })


@slicerPipeline(name="SurfaceToolbox.Decimate", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def decimation(mesh: vtkMRMLModelNode,
               reduction: Annotated[float, WithinRange(0, 1), Default(0.8), Decimals(2), SingleStep(0.01)],
               boundaryDeletion: Annotated[bool, Default(True)]) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "decimation", {
        "decimationReduction": str(reduction),
        "decimationBoundaryDeletion": formatBool(boundaryDeletion)
    })


@slicerPipeline(name="SurfaceToolbox.Smoothing.Taubin", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def taubinSmoothing(mesh: vtkMRMLModelNode,
                    iterations: Annotated[int, WithinRange(0, 100), Default(30)],
                    passBand: Annotated[float, WithinRange(0, 2), Default(0.1), Decimals(4), SingleStep(0.0001)],
                    boundarySmoothing: Annotated[bool, Default(True)]) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "smoothing", {
        "smoothingMethod": "Taubin",
        "smoothingTaubinIterations": str(iterations),
        "smoothingTaubinPassBand": str(passBand),
        "smoothingBoundarySmoothing": formatBool(boundarySmoothing),
    })


@slicerPipeline(name="SurfaceToolbox.Smoothing.Laplace", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def laplaceSmoothing(mesh: vtkMRMLModelNode,
                    iterations: Annotated[int, WithinRange(0, 500), Default(100)],
                    relaxation: Annotated[float, WithinRange(0, 1), Default(0.5), Decimals(1), SingleStep(0.1)],
                    boundarySmoothing: Annotated[bool, Default(True)]) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "smoothing", {
        "smoothingMethod": "Laplace",
        "smoothingLaplaceIterations": str(iterations),
        "smoothingLaplaceRelaxation": str(relaxation),
        "smoothingBoundarySmoothing": formatBool(boundarySmoothing),
    })


@slicerPipeline(name="SurfaceToolbox.FillHoles", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def fillHoles(mesh: vtkMRMLModelNode,
              maxHoleSize: Annotated[float, WithinRange(0, 1000), Default(1000), Decimals(1), SingleStep(0.1)]) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "fillHoles", {
        "fillHolesSize": str(maxHoleSize),
    })


@slicerPipeline(name="SurfaceToolbox.Normals", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def normals(mesh: vtkMRMLModelNode,
            autoOrientNormals: bool,
            flipNormals: bool,
            splitting: bool,
            featureAngleForSplitting: Annotated[float, WithinRange(0, 180), Default(30)]) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "normals", {
        "normalsOrient": formatBool(autoOrientNormals),
        "normalsFlip": formatBool(flipNormals),
        "normalsSplitting": formatBool(splitting),
        "normalsFeatureAngle": str(featureAngleForSplitting),
    })


@slicerPipeline(name="SurfaceToolbox.Mirror", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def mirrorMesh(mesh: vtkMRMLModelNode,
               mirrorX: bool,
               mirrorY: bool,
               mirrorZ: bool) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "mirror", {
        "mirrorX": formatBool(mirrorX),
        "mirrorY": formatBool(mirrorY),
        "mirrorZ": formatBool(mirrorZ),
    })


@slicerPipeline(name="SurfaceToolbox.ScaleMesh", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def scaleMesh(mesh: vtkMRMLModelNode,
              scaleX: Annotated[float, Minimum(0)],
              scaleY: Annotated[float, Minimum(0)],
              scaleZ: Annotated[float, Minimum(0)]) -> vtkMRMLModelNode:

    return _surfaceToolboxRun(mesh, "scale", {
        "scaleX": str(scaleX),
        "scaleY": str(scaleY),
        "scaleZ": str(scaleZ),
    })


@slicerPipeline(name="SurfaceToolbox.TranslateMesh", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def translateMesh(mesh: vtkMRMLModelNode,
                  translateX: float,
                  translateY: float,
                  translateZ: float) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "translate", {
        "translateX": str(translateX),
        "translateY": str(translateY),
        "translateZ": str(translateZ),
    })


@slicerPipeline(name="SurfaceToolbox.ExtractEdges", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def extractEdges(mesh: vtkMRMLModelNode,
              boundaryEdges: Annotated[bool, Default(True)],
              featureEdges: Annotated[bool, Default(True)],
              featureAngle: Annotated[float, WithinRange(0, 180), Default(20)],
              manifoldEdges: bool,
              nonManifoldEdges: bool) -> vtkMRMLModelNode:

    return _surfaceToolboxRun(mesh, "extractEdges", {
        "extractEdgesBoundary": formatBool(boundaryEdges),
        "extractEdgesFeature": formatBool(featureEdges),
        "extractEdgesFeatureAngle": str(featureAngle),
        "extractEdgesManifold": formatBool(manifoldEdges),
        "extractEdgesNonManifold": formatBool(nonManifoldEdges),
    })

@slicerPipeline(name="SurfaceToolbox.ExtractLargestComponent", dependencies=_surfaceToolboxDeps, categories=_surfaceToolboxCats)
def extractLargestComponent(mesh: vtkMRMLModelNode) -> vtkMRMLModelNode:
    return _surfaceToolboxRun(mesh, "connectivity", {})
