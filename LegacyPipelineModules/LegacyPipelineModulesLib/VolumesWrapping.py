import slicer
from LegacyPipelineCreator import slicerPipeline
from LegacyPipelineCreatorLib.PipelineBases import SinglePiecePipeline

@slicerPipeline
class ExportScalarVolumeToLabelMapVolume(SinglePiecePipeline):
  @staticmethod
  def GetName():
    return "Export Scalar Volume to LabelMap Volume"
  @staticmethod
  def GetInputType():
    return 'vtkMRMLScalarVolumeNode'
  @staticmethod
  def GetOutputType():
    return 'vtkMRMLLabelMapVolumeNode'
  @staticmethod
  def GetDependencies():
    return ['Volumes']
  @staticmethod
  def GetParameters():
    return []
  
  def __init__(self):
    super().__init__()

  def _RunImpl(self, inputNode):
    labelmap = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    slicer.modules.volumes.logic().CreateLabelVolumeFromVolume(slicer.mrmlScene, labelmap, inputNode)
    return labelmap

@slicerPipeline
class ExportLabelMapVolumeToScalarVolume(SinglePiecePipeline):
  @staticmethod
  def GetName():
    return "Export LabelMap Volume to Scalar Volume"
  @staticmethod
  def GetInputType():
    return 'vtkMRMLLabelMapVolumeNode'
  @staticmethod
  def GetOutputType():
    return 'vtkMRMLScalarVolumeNode'
  @staticmethod
  def GetDependencies():
    return ['Volumes']
  @staticmethod
  def GetParameters():
    return []
  
  def __init__(self):
    super().__init__()

  def _RunImpl(self, inputNode):
    scalar = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode')
    slicer.modules.volumes.logic().CreateScalarVolumeFromVolume(slicer.mrmlScene, scalar, inputNode)
    return scalar
