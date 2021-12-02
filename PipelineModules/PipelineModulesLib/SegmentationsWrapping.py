import vtk
import slicer
from PipelineCreator import slicerPipeline
from .PipelineParameters import BooleanParameter, FloatParameterWithSlider, OpenFileParameter, SaveFileParameter
from .Util import ScopedNode

@slicerPipeline
class ConvertModelToSegmentation(object):
    @staticmethod
    def GetName():
      return "ConvertModelToSegmentation"
    @staticmethod
    def GetParameters():
      return [
        ('Volume Spacing X', FloatParameterWithSlider(value=0.2, minimum=0.01, maximum=5, singleStep=0.01, decimals=2, suffix='mm')),
        ('Volume Spacing Y', FloatParameterWithSlider(value=0.2, minimum=0.01, maximum=5, singleStep=0.01, decimals=2, suffix='mm')),
        ('Volume Spacing Z', FloatParameterWithSlider(value=0.2, minimum=0.01, maximum=5, singleStep=0.01, decimals=2, suffix='mm')),
        ('Volume Margin X', FloatParameterWithSlider(value=10.0, minimum=0.1, maximum=20, singleStep=0.1, decimals=1, suffix='mm')),
        ('Volume Margin Y', FloatParameterWithSlider(value=10.0, minimum=0.1, maximum=20, singleStep=0.1, decimals=1, suffix='mm')),
        ('Volume Margin Z', FloatParameterWithSlider(value=10.0, minimum=0.1, maximum=20, singleStep=0.1, decimals=1, suffix='mm')),
      ]
    @staticmethod
    def GetInputType():
      return 'vtkMRMLModelNode'
    @staticmethod
    def GetOutputType():
      return 'vtkMRMLSegmentationNode'
    @staticmethod
    def GetDependencies():
      return ['Segmentations']

    def __init__(self):
      self._volumeSpacing = [0.2]*3
      self._volumeMargin = [10.0]*3

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


    def Run(self, input):
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
      referenceVolumeNode.SetOrigin(imageOrigin)
      referenceVolumeNode.SetSpacing(self._volumeSpacing)
      referenceVolumeNode.SetAndObserveImageData(imageData)
      referenceVolumeNode.CreateDefaultDisplayNodes()

      segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolumeNode)

      slicer.modules.segmentations.logic().ImportModelToSegmentationNode(input, segmentationNode)
      #TODO: should we delete the volume node if the segmentation node is deleted?

      return segmentationNode


@slicerPipeline
class SaveSegmentationToFile(object):
  @staticmethod
  def GetName():
    return "Save Segmentation to File"

  FileFilter = [
    'Segmentation (*.seg.nrrd)',
    'Segmentation (*.nrrd)',
  ]

  @staticmethod
  def GetParameters():
    return [
      ('Filename', SaveFileParameter(caption="Save Segmentation", filter=SaveSegmentationToFile.FileFilter)),
      ('Crop To Minimum Extent', BooleanParameter(False)),
    ]

  @staticmethod
  def GetInputType():
    return 'vtkMRMLSegmentationNode'

  @staticmethod
  def GetOutputType():
    return None

  @staticmethod
  def GetDependencies():
    return ['Segmentations']

  def __init__(self):
      self._filename = None
      self._cropToMinimumExtent = False

  def SetFilename(self, filename):
    self._filename = filename
  def GetFilename(self):
    return self._filename

  def SetCropToMinimumExtent(self, cropToMinimumExtent):
    self._cropToMinimumExtent = cropToMinimumExtent
  def GetCropToMinimumExtent(self):
    return self._cropToMinimumExtent

  def Run(self, input):
    with ScopedNode(slicer.vtkMRMLSegmentationStorageNode()) as store:
      store.SetFileName(self._filename)
      store.SetCropToMinimumExtent(self._cropToMinimumExtent)
      store.WriteData(input)


@slicerPipeline
class LoadSegmentationFromFile(object):
  @staticmethod
  def GetName():
    return "Load Segmentation from File"

  FileFilter = SaveSegmentationToFile.FileFilter

  @staticmethod
  def GetParameters():
    return [
      ('Filename', OpenFileParameter(caption='Load Segmentation', filter=LoadSegmentationFromFile.FileFilter)),
    ]

  @staticmethod
  def GetInputType():
    return None

  @staticmethod
  def GetOutputType():
    return 'vtkMRMLSegmentationNode'

  @staticmethod
  def GetDependencies():
    return ['Segmentations']

  def __init__(self):
    self._filename = None

  def SetFilename(self, filename):
    self._filename = filename
  def GetFilename(self):
    return self._filename

  def Run(self):
    return slicer.util.loadSegmentation(self._filename)
