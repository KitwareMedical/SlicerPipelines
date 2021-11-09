import slicer
from PipelineCreator import slicerPipeline
from .PipelineParameters import BooleanParameter, StringComboBoxParameter, FloatParameterWithSlider, IntegerParameterWithSlider
from SurfaceToolbox import SurfaceToolboxLogic

###############################################################################
class SurfaceToolboxBase(object):
  def __init__(self):
    self._parameterNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScriptedModuleNode")
    self._surfaceToolboxLogic = SurfaceToolboxLogic()
    self._surfaceToolboxLogic.setDefaultParameters(self._parameterNode)

    self.verboseRun = False

  @staticmethod
  def GetDependencies():
    return ['SurfaceToolbox']

  @property
  def parameterNode(self):
    return self._parameterNode

  @property
  def surfaceToolboxLogic(self):
    return self._surfaceToolboxLogic

  def GetInputType(self):
    return "vtkMRMLModelNode"

  def GetOutputType(self):
    return "vtkMRMLModelNode"

  def Run(self, input):
    if self.verboseRun:
      print("Running %s" % self.GetName())
      for paramName, _ in self.GetParameters():
        print("  %s = %s" % (paramName, self.__getattribute__('Get%s' % paramName.replace(' ', ''))()))

    outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    self.parameterNode.SetNodeReferenceID("inputModel", input.GetID())
    self.parameterNode.SetNodeReferenceID("outputModel", outputModel.GetID())
    self.surfaceToolboxLogic.applyFilters(self.parameterNode)

    return outputModel

###############################################################################
@slicerPipeline
class ScaleMesh(SurfaceToolboxBase):
  def __init__(self):
    SurfaceToolboxBase.__init__(self)
    self.parameterNode.SetParameter("scale", "true")

  @staticmethod
  def GetName():
    return "SurfaceToolbox.ScaleMesh"

  @staticmethod
  def GetParameters():
    return [
      ('ScaleX', FloatParameterWithSlider(value=0.5, minimum=0.0, maximum=50.0, singleStep=0.01)),
      ('ScaleY', FloatParameterWithSlider(value=0.5, minimum=0.0, maximum=50.0, singleStep=0.01)),
      ('ScaleZ', FloatParameterWithSlider(value=0.5, minimum=0.0, maximum=50.0, singleStep=0.01)),
    ]

  def SetScaleX(self, scale):
    self.parameterNode.SetParameter("scaleX", str(scale))
  def GetScaleX(self):
    return float(self.parameterNode.GetParameter("scaleX"))
  def SetScaleY(self, scale):
    self.parameterNode.SetParameter("scaleY", str(scale))
  def GetScaleY(self):
    return float(self.parameterNode.GetParameter("scaleY"))
  def SetScaleZ(self, scale):
    self.parameterNode.SetParameter("scaleZ", str(scale))
  def GetScaleZ(self):
    return float(self.parameterNode.GetParameter("scaleZ"))

###############################################################################
@slicerPipeline
class TranslateMesh(SurfaceToolboxBase):
  def __init__(self):
    SurfaceToolboxBase.__init__(self)
    self.parameterNode.SetParameter("translate", "true")

  @staticmethod
  def GetName():
    return "SurfaceToolbox.TranslateMesh"

  @staticmethod
  def GetParameters():
    return [
      ('TranslateX', FloatParameterWithSlider(value=0.5, minimum=-100.0, maximum=100.0, singleStep=0.01)),
      ('TranslateY', FloatParameterWithSlider(value=0.5, minimum=-100.0, maximum=100.0, singleStep=0.01)),
      ('TranslateZ', FloatParameterWithSlider(value=0.5, minimum=-100.0, maximum=100.0, singleStep=0.01)),
    ]

  def SetTranslateX(self, translate):
    self.parameterNode.SetParameter("translateX", str(translate))
  def GetTranslateX(self):
    return float(self.parameterNode.GetParameter("translateX"))
  def SetTranslateY(self, translate):
    self.parameterNode.SetParameter("translateY", str(translate))
  def GetTranslateY(self):
    return float(self.parameterNode.GetParameter("translateY"))
  def SetTranslateZ(self, translate):
    self.parameterNode.SetParameter("translateZ", str(translate))
  def GetTranslateZ(self):
    return float(self.parameterNode.GetParameter("translateZ"))
