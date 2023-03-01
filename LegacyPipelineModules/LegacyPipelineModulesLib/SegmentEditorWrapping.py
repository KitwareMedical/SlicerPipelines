import sys

import slicer
from LegacyPipelineCreator import slicerPipeline
from LegacyPipelineCreatorLib.PipelineBases import SinglePiecePipeline
from .PipelineParameters import FloatRangeParameter, IntegerParameter, StringComboBoxParameter, FloatParameterWithSlider
import SegmentEditorEffects

###############################################################################
class SegmentEditorBase(SinglePiecePipeline):
  def __init__(self):
    super().__init__()
    self._segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
    self._segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode')
    self._segmentEditorWidget.setMRMLSegmentEditorNode(self._segmentEditorNode)
    self._segmentEditorWidget.setMRMLScene(slicer.mrmlScene)

  def __del__(self):
    self._segmentEditorWidget.setMRMLScene(None)
    slicer.mrmlScene.RemoveNode(self._segmentEditorNode)

  @staticmethod
  def GetInputType():
    return "vtkMRMLSegmentationNode"

  @staticmethod
  def GetOutputType():
    return "vtkMRMLSegmentationNode"

  @staticmethod
  def GetDependencies():
    return ['SegmentEditor', 'Segmentations']

  def setMRMLScene(self, scene):
    self._segmentEditorWidget.setMRMLScene(scene)

  def _RunImpl(self, input):
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    itemID = shNode.GetItemByDataNode(input)
    newItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode, itemID)
    return self._RunNoCopy(shNode.GetItemDataNode(newItemID))

  def _RunNoCopy(self, input):
    self._segmentEditorWidget.setSegmentationNode(input)
    #important we set the segmentation node before the active effect name
    self._segmentEditorWidget.setActiveEffectByName(self.EffectName)
    self._segmentEditorWidget.activeEffect().self().onApply()
    return input


###############################################################################
@slicerPipeline
class SmoothingEffect(SegmentEditorBase):
  EffectName = 'Smoothing'
  DefaultKernelSize = 3.0
  DefaultMethod = 'Median'
  _methodConverter = {
     'Median': 'MEDIAN',
     'Gaussian': 'GAUSSIAN',
     'Opening': 'MORPHOLOGICAL_OPENING',
     'Closing': 'MORPHOLOGICAL_CLOSING',
     'Joint Smoothing': 'JOINT_TAUBIN',
  }
  @staticmethod
  def GetSmoothingMethods():
    return list(SmoothingEffect._methodConverter.keys())

  @staticmethod
  def GetName():
    return "SegmentEditor.Smoothing"

  @staticmethod
  def GetParameters():
    return [
      ('Smoothing Method', StringComboBoxParameter(SmoothingEffect.GetSmoothingMethods())),
      ('Kernel Size', FloatParameterWithSlider(value=SmoothingEffect.DefaultKernelSize, minimum=0.1, maximum=100.0, singleStep=0.01, decimals=1, suffix='mm')),
    ]

  def __init__(self):
    SegmentEditorBase.__init__(self)
    self._effect = self._segmentEditorWidget.effectByName(self.EffectName)
    self.SetKernelSize(self.DefaultKernelSize)
    self.SetSmoothingMethod(self.DefaultMethod)

  def SetSmoothingMethod(self, method):
    self._effect.setParameter("SmoothingMethod", self._methodConverter[method])

  def SetKernelSize(self, kernelSize):
    self._effect.setParameter("KernelSizeMm", kernelSize)

###############################################################################
@slicerPipeline
class MarginEffect(SegmentEditorBase):
  EffectName = 'Margin'
  DefaultMarginSize = 2.00
  DefaultOperation = 'Grow'
  @staticmethod
  def GetOperations():
    return ['Grow', 'Shrink']

  @staticmethod
  def GetName():
    return "SegmentEditor.Margin"
  @staticmethod
  def GetParameters():
    return [
      ('Operation', StringComboBoxParameter(MarginEffect.GetOperations())),
      ('Margin Size', FloatParameterWithSlider(value=MarginEffect.DefaultMarginSize, minimum=0.01, maximum=100.0, singleStep=0.01, decimals=2, suffix='mm')),
    ]

  def __init__(self):
    SegmentEditorBase.__init__(self)
    self._effect = self._segmentEditorWidget.effectByName(self.EffectName)
    #note: because the DefaultMarginSize is positive, we default to 'Grow'
    self._effect.setParameter("MarginSizeMm", self.DefaultMarginSize)

  def SetMarginSize(self, marginSize):
    """
    Sets the margin size, a positive, floating point value.
    """
    currentSize = self._effect.doubleParameter("MarginSizeMm")
    self._effect.setParameter("MarginSizeMm", marginSize if currentSize >= 0.0 else -marginSize)

  def SetOperation(self, operation):
    absCurrentSize = abs(self._effect.doubleParameter("MarginSizeMm"))
    self._effect.setParameter("MarginSizeMm", absCurrentSize if operation == "Grow" else -absCurrentSize)

###############################################################################
@slicerPipeline
class HollowEffect(SegmentEditorBase):
  EffectName = 'Hollow'
  DefaultShellThickness = 3.00
  _optionsConverter = {
    'Segment is Inside Surface': SegmentEditorEffects.INSIDE_SURFACE,
    'Segment is Medial Surface': SegmentEditorEffects.MEDIAL_SURFACE,
    'Segment is Outside Surface': SegmentEditorEffects.OUTSIDE_SURFACE,
  }
  DefaultShellOption = list(_optionsConverter.keys())[0]
  @staticmethod
  def GetShellOptions():
    return list(HollowEffect._optionsConverter.keys())

  @staticmethod
  def GetName():
    return "SegmentEditor.Hollow"
  @staticmethod
  def GetParameters():
    return [
      ('Shell Option', StringComboBoxParameter(HollowEffect.GetShellOptions())),
      ('Thickness', FloatParameterWithSlider(value=HollowEffect.DefaultShellThickness, minimum=0.01, maximum=100.0, singleStep=0.01, decimals=2, suffix='mm')),
    ]

  def __init__(self):
    SegmentEditorBase.__init__(self)
    self._effect = self._segmentEditorWidget.effectByName(self.EffectName)
    self.SetThickness(self.DefaultShellThickness)
    self.SetShellOption(self.DefaultShellOption)

  def SetThickness(self, thickness):
    self._effect.setParameter("ShellThicknessMm", thickness)

  def SetShellOption(self, option):
    self._effect.setParameter("ShellMode", HollowEffect._optionsConverter[option])

###############################################################################
@slicerPipeline
class IslandsEffect(SegmentEditorBase):
  EffectName = 'Islands'
  _operationsConverter = {
    'Keep largest island': SegmentEditorEffects.KEEP_LARGEST_ISLAND,
    'Remove small islands': SegmentEditorEffects.REMOVE_SMALL_ISLANDS,
  }
  DefaultOperation = list(_operationsConverter.keys())[0]
  MaximumNumberOfVoxels = 2**31 - 1
  @staticmethod
  def GetOperations():
    return list(IslandsEffect._operationsConverter.keys())

  @staticmethod
  def GetName():
    return "SegmentEditor.Islands"
  @staticmethod
  def GetParameters():
    return [
      ('Operation', StringComboBoxParameter(IslandsEffect.GetOperations())),
      ('Minimum Size', IntegerParameter(value=1000, minimum=1, maximum=IslandsEffect.MaximumNumberOfVoxels, singleStep=1, suffix=' voxels'))
    ]

  def __init__(self):
    SegmentEditorBase.__init__(self)
    self._effect = self._segmentEditorWidget.effectByName(self.EffectName)
    self.SetOperation(self.DefaultOperation)

  def SetOperation(self, operation):
    self._effect.setParameter("Operation", self._operationsConverter[operation])

  def SetMinimumSize(self, voxels):
    self._effect.setParameter("MinimumSize", voxels)

###############################################################################

# for thresholding we are going to go take a volume as an input
@slicerPipeline
class ThresholdingEffect(SegmentEditorBase):
  EffectName = 'Threshold'
  DefaultThresholdRange = (-100., 100.)

  @staticmethod
  def GetInputType():
    return 'vtkMRMLScalarVolumeNode'
  @staticmethod
  def GetName():
    return 'SegmentEditor.Thresholding'
  @staticmethod
  def GetParameters():
    return [
      ('Threshold Range', FloatRangeParameter(
        minimumValue=ThresholdingEffect.DefaultThresholdRange[0],
        maximumValue=ThresholdingEffect.DefaultThresholdRange[1],
        minimum=-sys.float_info.max,
        maximum=sys.float_info.max,
        singleStep=1,
        decimals=2)),
    ]
  def __init__(self):
    SegmentEditorBase.__init__(self)
    self._effect = self._segmentEditorWidget.effectByName(self.EffectName)
    self.SetThresholdRange(self.DefaultThresholdRange)

  def SetThresholdRange(self, range):
    self._effect.setParameter("MinimumThreshold", range[0])
    self._effect.setParameter("MaximumThreshold", range[1])

  def Run(self, input):
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    segmentationNode.CreateBinaryLabelmapRepresentation()
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(input)
    segmentationNode.GetSegmentation().AddEmptySegment()
    self._segmentEditorWidget.setMasterVolumeNode(input)
    return SegmentEditorBase._RunNoCopy(self, segmentationNode)
