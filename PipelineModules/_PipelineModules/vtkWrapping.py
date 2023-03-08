from typing import Annotated

import vtk

import slicer
from slicer.parameterNodeWrapper import (
    Decimals,
    Default,
    SingleStep,
    WithinRange,
)

from PipelineCreator import slicerPipeline


def vtkPolyDataPipelineImpl(filter_: vtk.vtkPolyDataAlgorithm,
                            inputMesh: slicer.vtkMRMLModelNode,
                            **kwargs):
    filter_.SetInputData(inputMesh.GetPolyData())
    for name, value in kwargs.items():
        getattr(filter_, f"Set{name}")(value)

    filter_.Update()

    outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    outputModel.SetAndObservePolyData(filter_.GetOutput())
    return outputModel


@slicerPipeline(name="vtkQuadricDecimation", categories=["VTK"])
def quadricDecimation(mesh: slicer.vtkMRMLModelNode,
                      targetReduction: Annotated[float, WithinRange(0, 1), Default(0.9), Decimals(2), SingleStep(0.01)],
                      volumePreservation: bool) -> slicer.vtkMRMLModelNode:
    return vtkPolyDataPipelineImpl(vtk.vtkQuadricDecimation(),
                                   mesh,
                                   TargetReduction=targetReduction,
                                   VolumePreservation=volumePreservation)


@slicerPipeline(name="vtkCleanPolyData", categories=["VTK"])
def cleanPolyData(mesh: slicer.vtkMRMLModelNode) -> slicer.vtkMRMLModelNode:
    return vtkPolyDataPipelineImpl(vtk.vtkCleanPolyData(), mesh)


@slicerPipeline(name="vtkConnectivityFilter.LargestRegion", categories=["VTK"])
def connectivityFilterLargestRegion(mesh: slicer.vtkMRMLModelNode,
                                    colorRegions: bool) -> slicer.vtkMRMLModelNode:
    filter_ = vtk.vtkConnectivityFilter()
    filter_.SetExtractionModeToLargestRegion()
    return vtkPolyDataPipelineImpl(filter_,
                                   mesh,
                                   ColorRegions=colorRegions)


@slicerPipeline(name="vtkConnectivityFilter.AllRegions", categories=["VTK"])
def connectivityFilterAllRegions(mesh: slicer.vtkMRMLModelNode,
                                 colorRegions: bool) -> slicer.vtkMRMLModelNode:
    filter_ = vtk.vtkConnectivityFilter()
    filter_.SetExtractionModeToAllRegions()
    return vtkPolyDataPipelineImpl(filter_,
                                   mesh,
                                   ColorRegions=colorRegions)


@slicerPipeline(name="vtkDecimatePro", categories=["VTK"])
def decimatePro(mesh: slicer.vtkMRMLModelNode,
                targetReduction: Annotated[float, WithinRange(0, 1), Default(0.9), Decimals(2), SingleStep(0.01)],
                preserveTopology: bool,
                boundaryVertexDeletion: bool,
                splitting: bool,
                splitAngle: Annotated[float, WithinRange(0, 180), Default(75), Decimals(1), SingleStep(0.1)],
                featureAngle: Annotated[float, WithinRange(0, 180), Default(15), Decimals(1), SingleStep(0.1)],
                degree: Annotated[int, WithinRange(3, 100), Default(25)]) -> slicer.vtkMRMLModelNode:
    return vtkPolyDataPipelineImpl(vtk.vtkDecimatePro(),
                                   mesh,
                                   TargetReduction=targetReduction,
                                   PreserveTopology=preserveTopology,
                                   BoundaryVertexDeletion=boundaryVertexDeletion,
                                   Splitting=splitting,
                                   SplitAngle=splitAngle,
                                   FeatureAngle=featureAngle,
                                   Degree=degree)


@slicerPipeline(name="vtkFillHoles", categories=["VTK"])
def fillHoles(mesh: slicer.vtkMRMLModelNode,
              holeSize: Annotated[float, WithinRange(0, 1000), Default(1000), Decimals(2), SingleStep(0.1)]) -> slicer.vtkMRMLModelNode:
    return vtkPolyDataPipelineImpl(vtk.vtkFillHolesFilter(),
                                   mesh,
                                   HoleSize=holeSize)


@slicerPipeline(name="vtkPolyDataNormals", categories=["VTK"])
def polyDataNormals(mesh: slicer.vtkMRMLModelNode,
                    autoOrientNormals: bool,
                    splitting: Annotated[bool, Default(True)],
                    featureAngle: Annotated[float, WithinRange(0, 180), Default(30), Decimals(1), SingleStep(0.1)],
                    consistency: bool,
                    computePointNormals: Annotated[bool, Default(True)],
                    computeCellNormals: bool,
                    flipNormals: bool,
                    nonManifoldTraversal: Annotated[bool, Default(True)]) -> slicer.vtkMRMLModelNode:
    return vtkPolyDataPipelineImpl(vtk.vtkPolyDataNormals(),
                                   mesh,
                                   AutoOrientNormals=autoOrientNormals,
                                   Splitting=splitting,
                                   Consistency=consistency,
                                   ComputePointNormals=computePointNormals,
                                   ComputeCellNormals=computeCellNormals,
                                   FlipNormals=flipNormals,
                                   NonManifoldTraversal=nonManifoldTraversal,
                                   FeatureAngle=featureAngle)


@slicerPipeline(name="vtkSmoothPolyDataFilter", categories=["VTK"])
def smoothPolyDataFilter(mesh: slicer.vtkMRMLModelNode,
                         relaxationFactor: Annotated[float, WithinRange(0, 1), Default(0.8), Decimals(2), SingleStep(0.01)],
                         boundarySmoothing: Annotated[bool, Default(True)],
                         iterations: Annotated[int, WithinRange(1, 100), Default(30)],
                         featureAngle: Annotated[float, WithinRange(0, 180), Default(45), Decimals(1), SingleStep(0.1)],
                         edgeAngle: Annotated[float, WithinRange(0, 180), Default(15), Decimals(1), SingleStep(0.1)]) -> slicer.vtkMRMLModelNode:
    return vtkPolyDataPipelineImpl(vtk.vtkSmoothPolyDataFilter(),
                                   mesh,
                                   RelaxationFactor=relaxationFactor,
                                   BoundarySmoothing=boundarySmoothing,
                                   NumberOfIterations=iterations,
                                   FeatureAngle=featureAngle,
                                   EdgeAngle=edgeAngle)


@slicerPipeline(name="vtkWindowedSincPolyDataFilter", categories=["VTK"])
def windowedSincPolyDataFilter(mesh: slicer.vtkMRMLModelNode,
                               iterations: Annotated[int, WithinRange(1, 100), Default(30)],
                               passBand: Annotated[float, WithinRange(0, 2), Default(0.5), Decimals(2), SingleStep(0.01)],
                               boundarySmoothing: Annotated[bool, Default(True)],
                               normalizeCoordinates: bool,
                               nonManifoldSmoothing: bool,
                               featureAngle: Annotated[float, WithinRange(0, 180), Default(45), Decimals(1), SingleStep(0.1)],
                               edgeAngle: Annotated[float, WithinRange(0, 180), Default(15), Decimals(1), SingleStep(0.1)]) -> slicer.vtkMRMLModelNode:
    return vtkPolyDataPipelineImpl(vtk.vtkWindowedSincPolyDataFilter(),
                                   mesh,
                                   NumberOfIterations=iterations,
                                   PassBand=passBand,
                                   BoundarySmoothing=boundarySmoothing,
                                   NormalizeCoordinates=normalizeCoordinates,
                                   NonManifoldSmoothing=nonManifoldSmoothing,
                                   FeatureAngle=featureAngle,
                                   EdgeAngle=edgeAngle)
