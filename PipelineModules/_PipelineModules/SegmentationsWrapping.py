from typing import Annotated

import vtk
import slicer

from slicer.parameterNodeWrapper import (
    parameterPack,

    Decimals,
    Default,
    Minimum,
    SingleStep,
)

from slicer import (
    vtkMRMLLabelMapVolumeNode,
    vtkMRMLModelNode,
    vtkMRMLScalarVolumeNode,
    vtkMRMLSegmentationNode,
)

from PipelineCreator import slicerPipeline


@slicerPipeline(name="Export First Segment to Model", categories=["Conversions", "Segmentation Operations"])
def exportFirstSegmentToModel(segmentation: vtkMRMLSegmentationNode) -> vtkMRMLModelNode:
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    exportFolderItemId = shNode.CreateFolderItem(shNode.GetSceneItemID(), "TempSegmentToModel")
    slicer.modules.segmentations.logic().ExportAllSegmentsToModels(segmentation, exportFolderItemId)

    children = vtk.vtkIdList()
    shNode.GetItemChildren(exportFolderItemId, children)
    if children.GetNumberOfIds() == 0:
        raise Exception("Export Segmentation to Model pipeline: No models were created")

    modelShId = children.GetId(0)
    shNode.SetItemParent(modelShId, shNode.GetItemParent(exportFolderItemId))
    shNode.RemoveItem(exportFolderItemId)

    return shNode.GetItemDataNode(modelShId)


@slicerPipeline(name="Export Segmentation to LabelMap", categories=["Conversions", "Segmentation Operations"])
def exportSegmentationToLabelMap(segmentation: vtkMRMLSegmentationNode) -> vtkMRMLLabelMapVolumeNode:
    outputNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
      segmentation,
      outputNode,
      slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY)
    return outputNode


@slicerPipeline(name="Export LabelMap to Segmentation", categories=["Conversions", "LabelMap Operations"])
def exportLabelMapToSegmentation(labelMap: vtkMRMLLabelMapVolumeNode) -> vtkMRMLSegmentationNode:
    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelMap, seg)
    seg.CreateClosedSurfaceRepresentation()
    return seg


@slicerPipeline(name="Export Model to Segmentation - Reference Volume", categories=["Conversions", "Model Operations"])
def exportModelToSegmentationReferenceVolume(model: vtkMRMLModelNode,
                                             referenceVolume: vtkMRMLScalarVolumeNode) -> vtkMRMLSegmentationNode:
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolume)
    slicer.modules.segmentations.logic().ImportModelToSegmentationNode(model, segmentationNode)
    return segmentationNode


@parameterPack
class SegmentationAndReferenceVolume:
    segmentation: vtkMRMLSegmentationNode
    referenceVolume: vtkMRMLScalarVolumeNode


@slicerPipeline(name="Export Model to Segmentation - Spacing", categories=["Conversions", "Model Operations"])
def exportModelToSegmentationSpacing(model: vtkMRMLModelNode,
                                     spacingX: Annotated[float, Minimum(0), Default(0.1), Decimals(2), SingleStep(0.01)],
                                     spacingY: Annotated[float, Minimum(0), Default(0.1), Decimals(2), SingleStep(0.01)],
                                     spacingZ: Annotated[float, Minimum(0), Default(0.1), Decimals(2), SingleStep(0.01)],
                                     marginX: Annotated[float, Minimum(0), Default(1), Decimals(1), SingleStep(0.1)],
                                     marginY: Annotated[float, Minimum(0), Default(1), Decimals(1), SingleStep(0.1)],
                                     marginZ: Annotated[float, Minimum(0), Default(1), Decimals(1), SingleStep(0.1)]) -> SegmentationAndReferenceVolume:
    volumeMargin = [marginX, marginY, marginZ]
    volumeSpacing = [spacingX, spacingY, spacingZ]
    
    #create reference volume
    bounds = [0.]*6
    model.GetBounds(bounds)
    imageData = vtk.vtkImageData()
    imageSize = [int((bounds[axis * 2 + 1] - bounds[axis * 2] + volumeMargin[axis] * 2.0) / volumeSpacing[axis]) for axis in range(3)]
    imageOrigin = [ bounds[axis * 2] - volumeMargin[axis] for axis in range(3) ]
    imageData.SetDimensions(imageSize)
    imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
    imageData.GetPointData().GetScalars().Fill(0)
    referenceVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    referenceVolumeNode.SetName(f"{model.GetName()}_ReferenceVolume")
    referenceVolumeNode.SetOrigin(imageOrigin)
    referenceVolumeNode.SetSpacing(volumeSpacing)
    referenceVolumeNode.SetAndObserveImageData(imageData)
    referenceVolumeNode.CreateDefaultDisplayNodes()

    segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolumeNode)
    slicer.modules.segmentations.logic().ImportModelToSegmentationNode(model, segmentationNode)

    return SegmentationAndReferenceVolume(segmentationNode, referenceVolumeNode)

