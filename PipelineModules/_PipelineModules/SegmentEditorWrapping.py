import enum
from typing import Annotated

import slicer
from slicer.parameterNodeWrapper import (
    Decimals,
    Default,
    FloatRange,
    Minimum,
    RangeBounds,
    SingleStep,
    WithinRange,
)
import SegmentEditorEffects
from PipelineCreator import slicerPipeline


class SegmentEditorHelper:
    def __init__(self, effectName):
        self.segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        self.segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode')
        self.segmentEditorWidget.setMRMLSegmentEditorNode(self.segmentEditorNode)
        self.segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        self.effectName = effectName
        self.effectParameters = {}

    def __del__(self):
        self.segmentEditorWidget.setMRMLScene(None)
        slicer.mrmlScene.RemoveNode(self.segmentEditorNode)
        self.segmentEditorWidget.deleteLater()

    def run(self, inputSeg):
        # need to clone the segmentation and then make the in-place adjustments
        shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
        itemID = shNode.GetItemByDataNode(inputSeg)
        newItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode, itemID)
        return self.runInPlace(shNode.GetItemDataNode(newItemID))

    def runInPlace(self, inputSeg):
        self.segmentEditorWidget.setSegmentationNode(inputSeg)
        #important we set the segmentation node before the active effect name
        self.segmentEditorWidget.setActiveEffectByName(self.effectName)
        for name, value in self.effectParameters.items():
            self.segmentEditorWidget.activeEffect().setParameter(name, value)
        self.segmentEditorWidget.activeEffect().self().onApply()
        return inputSeg


class SmoothingMethod(enum.Enum):
    Median = "MEDIAN"
    Gaussian = "GAUSSIAN"
    Opening = "MORPHOLOGICAL_OPENING"
    Closing = "MORPHOLOGICAL_CLOSING"
    JointSmoothing = "JOINT_TAUBIN"


@slicerPipeline(name="SegmentEditor.Smoothing", categories=["SegmentEditor", "Segmentation Operations"])
def smoothing(segmentation: slicer.vtkMRMLSegmentationNode,
              method: SmoothingMethod,
              kernelSize: Annotated[int, Minimum(0), Default(3)]) -> slicer.vtkMRMLSegmentationNode:
    helper = SegmentEditorHelper("Smoothing")
    helper.effectParameters = {
        "SmoothingMethod": method.value,
        "KernelSizeMm": kernelSize,
    }
    return helper.run(segmentation)


class MarginMethod(enum.Enum):
    Grow = "Grow"
    Shrink = "Shrink"


@slicerPipeline(name="SegmentEditor.Margin", categories=["SegmentEditor", "Segmentation Operations"])
def margin(segmentation: slicer.vtkMRMLSegmentationNode,
           method: MarginMethod,
           marginSize: Annotated[float, Minimum(0), Default(2), Decimals(2), SingleStep(0.01)]) -> slicer.vtkMRMLSegmentationNode:
    helper = SegmentEditorHelper("Margin")
    helper.effectParameters = {
        "MarginSizeMm": marginSize if method == MarginMethod.Grow else -marginSize,
    }
    return helper.run(segmentation)


class HollowMethod(enum.Enum):
    InsideSurface = SegmentEditorEffects.INSIDE_SURFACE
    MedialSurface = SegmentEditorEffects.MEDIAL_SURFACE
    OutsideSurface = SegmentEditorEffects.OUTSIDE_SURFACE

    def label(self):
        if self is HollowMethod.InsideSurface:
            return "Segment is Inside Surface"
        if self is HollowMethod.MedialSurface:
            return "Segment is Medial Surface"
        if self is HollowMethod.OutsideSurface:
            return "Segment is Outside Surface"
        return "Unknown HollowMethod"


@slicerPipeline(name="SegmentEditor.Hollow", categories=["SegmentEditor", "Segmentation Operations"])
def hollow(segmentation: slicer.vtkMRMLSegmentationNode,
           method: HollowMethod,
           thickness: Annotated[float, WithinRange(0.01, 100), Default(3), Decimals(2), SingleStep(0.01)]) -> slicer.vtkMRMLSegmentationNode:
    helper = SegmentEditorHelper("Hollow")
    helper.effectParameters = {
        "ShellMode": method.value,
        "ShellThicknessMm": thickness,
    }
    return helper.run(segmentation)


@slicerPipeline(name="SegmentEditor.Islands.KeepLargest", categories=["SegmentEditor", "Segmentation Operations"])
def islandsKeepLargest(segmentation: slicer.vtkMRMLSegmentationNode,
                       minimumSizeVoxels: Annotated[int, Minimum(0), Default(1000)]) -> slicer.vtkMRMLSegmentationNode:
    helper = SegmentEditorHelper("Islands")
    helper.effectParameters = {
        "Operation": SegmentEditorEffects.KEEP_LARGEST_ISLAND,
        "MinimumSize": minimumSizeVoxels,
    }
    return helper.run(segmentation)


@slicerPipeline(name="SegmentEditor.Islands.RemoveSmall", categories=["SegmentEditor", "Segmentation Operations"])
def islandsRemoveSmall(segmentation: slicer.vtkMRMLSegmentationNode,
                       minimumSizeVoxels: Annotated[int, Minimum(0), Default(1000)]) -> slicer.vtkMRMLSegmentationNode:
    helper = SegmentEditorHelper("Islands")
    helper.effectParameters = {
        "Operation": SegmentEditorEffects.REMOVE_SMALL_ISLANDS,
        "MinimumSize": minimumSizeVoxels,
    }
    return helper.run(segmentation)


@slicerPipeline(name="SegmentEditor.Thresholding", categories=["SegmentEditor", "Scalar Volume Operations"])
def thresholding(volume: slicer.vtkMRMLScalarVolumeNode,
                 thresholdRange: Annotated[FloatRange, RangeBounds(-3000, 3000), Default(FloatRange(-100, 100)), SingleStep(1), Decimals(2)]
                ) -> slicer.vtkMRMLSegmentationNode:
    helper = SegmentEditorHelper("Threshold")
    helper.effectParameters = {
        "MinimumThreshold": thresholdRange.minimum,
        "MaximumThreshold": thresholdRange.maximum,
    }
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    segmentationNode.CreateBinaryLabelmapRepresentation()
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(volume)
    segmentationNode.GetSegmentation().AddEmptySegment()
    helper.segmentEditorWidget.setMasterVolumeNode(volume)
    return helper.runInPlace(segmentationNode)
