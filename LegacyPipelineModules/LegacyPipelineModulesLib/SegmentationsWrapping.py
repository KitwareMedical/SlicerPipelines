import copy
import vtk
import slicer
from LegacyPipelineCreator import slicerPipeline
from LegacyPipelineCreatorLib.PipelineBases import SinglePiecePipeline
from .PipelineParameters import FloatParameterWithSlider, StringParameter

@slicerPipeline
class ExportModelToSegmentation(SinglePiecePipeline):
    DefaultVolumeName = "PipelineSegmentationVolume"
    DefaultVolumeSpacing = [0.2, 0.2, 0.2]
    DefaultVolumeMargin = [10.0, 10.0, 10.0]
    @staticmethod
    def GetName():
      return "Export Model to Segmentation"
    @staticmethod
    def GetParameters():
      return [
        ('Volume Name', StringParameter(defaultText=ExportModelToSegmentation.DefaultVolumeName, placeholderText="Enter a name")),
        ('Volume Spacing X', FloatParameterWithSlider(value=ExportModelToSegmentation.DefaultVolumeSpacing[0], minimum=0.01, maximum=5, singleStep=0.01, decimals=2, suffix='mm')),
        ('Volume Spacing Y', FloatParameterWithSlider(value=ExportModelToSegmentation.DefaultVolumeSpacing[1], minimum=0.01, maximum=5, singleStep=0.01, decimals=2, suffix='mm')),
        ('Volume Spacing Z', FloatParameterWithSlider(value=ExportModelToSegmentation.DefaultVolumeSpacing[2], minimum=0.01, maximum=5, singleStep=0.01, decimals=2, suffix='mm')),
        ('Volume Margin X', FloatParameterWithSlider(value=ExportModelToSegmentation.DefaultVolumeMargin[0], minimum=0.1, maximum=20, singleStep=0.1, decimals=1, suffix='mm')),
        ('Volume Margin Y', FloatParameterWithSlider(value=ExportModelToSegmentation.DefaultVolumeMargin[1], minimum=0.1, maximum=20, singleStep=0.1, decimals=1, suffix='mm')),
        ('Volume Margin Z', FloatParameterWithSlider(value=ExportModelToSegmentation.DefaultVolumeMargin[2], minimum=0.1, maximum=20, singleStep=0.1, decimals=1, suffix='mm')),
      ]
    @staticmethod
    def GetInputType():
      return 'vtkMRMLModelNode'
    @staticmethod
    def GetOutputType():
      return 'vtkMRMLSegmentationNode'
    @staticmethod
    def GetDependencies():
      return ['Segmentations', 'Models']

    def __init__(self):
      super().__init__()
      self._volumeName = self.DefaultVolumeName
      self._volumeSpacing = copy.deepcopy(ExportModelToSegmentation.DefaultVolumeSpacing)
      self._volumeMargin = copy.deepcopy(ExportModelToSegmentation.DefaultVolumeMargin)

    def SetVolumeName(self, name):
      self._volumeName = name

    def SetVolumeSpacingX(self, spacing):
      self._volumeSpacing[0] = spacing
    def SetVolumeSpacingY(self, spacing):
      self._volumeSpacing[1] = spacing
    def SetVolumeSpacingZ(self, spacing):
      self._volumeSpacing[2] = spacing

    def SetVolumeMarginX(self, margin):
      self._volumeMargin[0] = margin
    def SetVolumeMarginY(self, margin):
      self._volumeMargin[1] = margin
    def SetVolumeMarginZ(self, margin):
      self._volumeMargin[2] = margin


    def _RunImpl(self, input):
      segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
      segmentationNode.CreateDefaultDisplayNodes()

      #create reference volume
      bounds = [0.]*6
      input.GetBounds(bounds)
      imageData = vtk.vtkImageData()
      imageSize = [ int((bounds[axis*2+1]-bounds[axis*2]+self._volumeMargin[axis]*2.0)/self._volumeSpacing[axis]) for axis in range(3) ]
      imageOrigin = [ bounds[axis*2]-self._volumeMargin[axis] for axis in range(3) ]
      imageData.SetDimensions(imageSize)
      imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
      imageData.GetPointData().GetScalars().Fill(0)
      referenceVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
      referenceVolumeNode.SetName(self._volumeName)
      referenceVolumeNode.SetOrigin(imageOrigin)
      referenceVolumeNode.SetSpacing(self._volumeSpacing)
      referenceVolumeNode.SetAndObserveImageData(imageData)
      referenceVolumeNode.CreateDefaultDisplayNodes()

      segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolumeNode)

      slicer.modules.segmentations.logic().ImportModelToSegmentationNode(input, segmentationNode)
      #TODO: should we delete the volume node if the segmentation node is deleted?

      return segmentationNode

@slicerPipeline
class ExportSegmentationToModel(SinglePiecePipeline):
  @staticmethod
  def GetName():
    return "Export Segmentation to Model"
  @staticmethod
  def GetInputType():
    return 'vtkMRMLSegmentationNode'
  @staticmethod
  def GetOutputType():
    return 'vtkMRMLModelNode'
  @staticmethod
  def GetDependencies():
    return ['Segmentations', 'Models']
  @staticmethod
  def GetParameters():
    return []

  def __init__(self):
    super().__init__()

  def _RunImpl(self, inputNode):
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    exportFolderItemId = shNode.CreateFolderItem(shNode.GetSceneItemID(), "TempSegmentToModel")
    slicer.modules.segmentations.logic().ExportAllSegmentsToModels(inputNode, exportFolderItemId)

    children = vtk.vtkIdList()
    shNode.GetItemChildren(exportFolderItemId, children)
    if children.GetNumberOfIds() == 0:
      raise Exception(self.GetName() + ": No models were created")

    modelShId = children.GetId(0)
    shNode.SetItemParent(modelShId, shNode.GetItemParent(exportFolderItemId))
    shNode.RemoveItem(exportFolderItemId)

    return shNode.GetItemDataNode(modelShId)

@slicerPipeline
class ExportSegmentationToLabelMap(SinglePiecePipeline):
  @staticmethod
  def GetName():
    return "Export Segmentation to LabelMap"
  @staticmethod
  def GetInputType():
    return 'vtkMRMLSegmentationNode'
  @staticmethod
  def GetOutputType():
    return 'vtkMRMLLabelMapVolumeNode'
  @staticmethod
  def GetDependencies():
    return ['Segmentations', 'Volumes']
  @staticmethod
  def GetParameters():
    return []
  
  def __init__(self):
    super().__init__()

  def _RunImpl(self, inputNode):
    outputNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
      inputNode,
      outputNode,
      slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY)
    return outputNode

@slicerPipeline
class ExportLabelMapVolumeToSegmentation(SinglePiecePipeline):
  @staticmethod
  def GetName():
    return "Export LabelMap Volume to Segmentation"
  @staticmethod
  def GetInputType():
    return 'vtkMRMLLabelMapVolumeNode'
  @staticmethod
  def GetOutputType():
    return 'vtkMRMLSegmentationNode'
  @staticmethod
  def GetDependencies():
    return ['Segmentations', 'Volumes']
  @staticmethod
  def GetParameters():
    return []
  
  def __init__(self):
    super().__init__()

  def _RunImpl(self, inputNode):
    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(inputNode, seg)
    seg.CreateClosedSurfaceRepresentation()
    return seg
