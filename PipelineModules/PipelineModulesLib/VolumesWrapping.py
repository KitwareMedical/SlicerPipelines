import slicer
from PipelineCreator import slicerPipeline
from PipelineCreatorLib.PipelineBases import SinglePiecePipeline

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
