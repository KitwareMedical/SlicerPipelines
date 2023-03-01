import vtk
import slicer

from MRMLCorePython import (
    vtkMRMLLabelMapVolumeNode,
    vtkMRMLModelNode,
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
