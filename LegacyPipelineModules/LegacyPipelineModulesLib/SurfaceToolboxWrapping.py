try:
  import slicer
  from LegacyPipelineCreator import slicerPipeline
  from LegacyPipelineCreatorLib.PipelineBases import SinglePiecePipeline
  from .PipelineParameters import BooleanParameter, FloatParameterWithSlider
  from SurfaceToolbox import SurfaceToolboxLogic

  ###############################################################################
  class SurfaceToolboxBase(SinglePiecePipeline):
    def __init__(self):
      super().__init__()
      self._parameterNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScriptedModuleNode")
      self._surfaceToolboxLogic = SurfaceToolboxLogic()
      self._surfaceToolboxLogic.setDefaultParameters(self._parameterNode)

      self.verboseRun = False

    def __del__(self):
      slicer.mrmlScene.RemoveNode(self._parameterNode)

    @staticmethod
    def GetDependencies():
      return ['SurfaceToolbox']

    @property
    def parameterNode(self):
      return self._parameterNode

    @property
    def surfaceToolboxLogic(self):
      return self._surfaceToolboxLogic

    @staticmethod
    def GetInputType():
      return "vtkMRMLModelNode"

    @staticmethod
    def GetOutputType():
      return "vtkMRMLModelNode"

    def _RunImpl(self, input):
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

  ###############################################################################
  @slicerPipeline
  class MirrorMesh(SurfaceToolboxBase):
    def __init__(self):
      SurfaceToolboxBase.__init__(self)
      self.parameterNode.SetParameter("mirror", "true")

    @staticmethod
    def GetName():
      return "SurfaceToolbox.Mirror"

    @staticmethod
    def GetParameters():
      return [
        ('X Axis', BooleanParameter(False)),
        ('Y Axis', BooleanParameter(False)),
        ('Z Axis', BooleanParameter(False)),
      ]

    def SetXAxis(self, mirror):
      self.parameterNode.SetParameter("mirrorX", "true" if mirror else "false")
    def SetYAxis(self, mirror):
      self.parameterNode.SetParameter("mirrorY", "true" if mirror else "false")
    def SetZAxis(self, mirror):
      self.parameterNode.SetParameter("mirrorZ", "true" if mirror else "false")

    def GetXAxis(self):
      return self.parameterNode.GetParameter("mirrorX") == "true"
    def GetYAxis(self):
      return self.parameterNode.GetParameter("mirrorY") == "true"
    def GetZAxis(self):
      return self.parameterNode.GetParameter("mirrorZ") == "true"
except ImportError:
  pass
