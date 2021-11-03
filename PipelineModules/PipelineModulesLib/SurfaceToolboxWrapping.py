import slicer
from PipelineCreator import slicerPipeline
from .PipelineParameters import BooleanParameter, StringComboBoxParameter, FloatParameter, IntegerParameter
from SurfaceToolbox import SurfaceToolboxLogic

###############################################################################
class SurfaceToolboxBase(object):
  def __init__(self):
    self._parameterNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLScriptedModuleNode")
    slicer.mrmlScene.AddNode(self._parameterNode)
    self._surfaceToolboxLogic = SurfaceToolboxLogic()
    self._surfaceToolboxLogic.setDefaultParameters(self._parameterNode)

    self.verboseRun = False

  def GetDependencies(self):
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
class Decimation(SurfaceToolboxBase):
  def __init__(self):
    SurfaceToolboxBase.__init__(self)
    self.parameterNode.SetParameter("decimation", "true")

  def GetName(self):
    return "SurfaceToolbox.Decimation"

  @staticmethod
  def GetParameters():
    return [
      ('Reduction', FloatParameter(value=0.8, minimum=0.0, maximum=1.0, singleStep=0.01)),
      ('Boundary Deletion', BooleanParameter(True)),
    ]

  def SetReduction(self, reduction):
    self.parameterNode.SetParameter("decimationReduction", str(reduction))

  def GetReduction(self):
    return float(self.parameterNode.GetParameter("decimationReduction"))

  def SetBoundaryDeletion(self, boundaryDeletion):
    self.parameterNode.SetParameter("decimationBoundaryDeletion", str(boundaryDeletion).lower())

  def GetBoundaryDeletion(self):
    return self.parameterNode.GetParameter("decimationBoundaryDeletion").lower() == "true"

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
      ('ScaleX', FloatParameter(value=0.5, minimum=0.0, maximum=50.0, singleStep=0.01)),
      ('ScaleY', FloatParameter(value=0.5, minimum=0.0, maximum=50.0, singleStep=0.01)),
      ('ScaleZ', FloatParameter(value=0.5, minimum=0.0, maximum=50.0, singleStep=0.01)),
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
class Smoothing(SurfaceToolboxBase):
  def __init__(self):
    SurfaceToolboxBase.__init__(self)
    self.parameterNode.SetParameter("smoothing", "true")

  @staticmethod
  def GetName():
    return "SurfaceToolbox.Smoothing"

  @staticmethod
  def GetParameters():
    return [
      ('Method', StringComboBoxParameter(['Laplace', 'Taubin'])),
      ('Iterations', IntegerParameter(value=100, minimum=0, maximum=500, singleStep=1)),
      ('Relaxation', FloatParameter(value=0.5, minimum=0.0, maximum=1.0, singleStep=0.1)),
      ('Boundary Smoothing', BooleanParameter(True)),
    ]

  def SetMethod(self, method):
    self.parameterNode.SetParameter("smoothingMethod", method)
  def GetMethod(self):
    return self.parameterNode.GetParameter("smoothingMethod")

  def SetIterations(self, iterations):
    self.parameterNode.SetParameter("smoothingLaplaceIterations", str(iterations))
    self.parameterNode.SetParameter("smoothingTaubinIterations", str(iterations))
  def GetIterations(self):
    if self.GetMethod() == "Laplace":
      return int(self.parameterNode.GetParameter("smoothingLaplaceIterations"))
    else:
      return int(self.parameterNode.GetParameter("smoothingTaubinIterations"))

  def SetRelaxation(self, relaxation):
    self.parameterNode.SetParameter("smoothingLaplaceRelaxation", str(relaxation))
  def GetRelaxation(self):
    return float(self.parameterNode.GetParameter("smoothingLaplaceRelaxation"))

  def SetBoundarySmoothing(self, boundarySmoothing):
    self.parameterNode.SetParameter("smoothingBoundarySmoothing", "true" if boundarySmoothing else "false")
  def GetBoundarySmoothing(self):
    return self.parameterNode.GetParameter("smoothingBoundarySmoothing") == "true"

###############################################################################
@slicerPipeline
class Cleaner(SurfaceToolboxBase):
  def __init__(self):
    SurfaceToolboxBase.__init__(self)
    self.parameterNode.SetParameter("clean", "true")

  @staticmethod
  def GetName():
    return "SurfaceToolbox.Cleaner"

  @staticmethod
  def GetParameters():
    return []

  def Run(self, input):
    print("Running "+ self.GetName())
    return input
