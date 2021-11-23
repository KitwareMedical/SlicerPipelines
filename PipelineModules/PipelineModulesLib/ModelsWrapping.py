from os import stat
import slicer
from PipelineCreator import slicerPipeline
from .PipelineParameters import SaveFileParameter, StringComboBoxParameter

@slicerPipeline
class SaveModelToFile(object):
  @staticmethod
  def GetName():
    return "Save Model to File"

  @staticmethod
  def GetParameters():
    return [
      ('Filename', SaveFileParameter(filter=[
        'Poly Data (*.vtk)',
        'XML Poly Data (*.vtp)',
        'STL (*.stl)',
        'PLY (*.ply)',
        'Wavefront OBJ (*.obj)',
        'XML Unstructured Grid (*.vtu)',
        ])),
      ('Coordinate System', StringComboBoxParameter(['LPS', 'RAS']))
    ]

  @staticmethod
  def GetInputType():
    return 'vtkMRMLModelNode'

  @staticmethod
  def GetOutputType():
    return None

  @staticmethod
  def GetDependencies():
    return ['Models']

  def __init__(self):
    self._filename = None
    self._coordinateSystem = 'LPS'

  def SetFilename(self, filename):
    self._filename = filename
  def GetFilename(self):
    return self._filename

  def SetCoordinateSystem(self, coord):
    if coord.upper() not in ('LPS', 'RAS'):
      raise Exception('Unknown coordinate system: ' + coord)
    self._coordinateSystem = coord.upper()
  def GetCoordinateSystem(self):
    return self._coordinateSystem

  def Run(self, input):
    store = input.CreateDefaultStorageNode()
    store.SetFileName(self._filename)
    store.SetCoordinateSystem(slicer.vtkMRMLModelStorageNode.GetCoordinateSystemFromString(self._coordinateSystem))
    store.WriteData(input)

    slicer.mrmlScene.RemoveNode(store)
