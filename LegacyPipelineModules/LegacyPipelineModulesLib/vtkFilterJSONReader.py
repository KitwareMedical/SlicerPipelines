import json
import os
import textwrap

import slicer # Note: this import may show up as unused in linting, but it is needed for the exec calls to work
import vtk # Note: this import may show up as unused in linting, but it is needed for the exec calls to work
from .PipelineParameters import BooleanParameter, StringComboBoxParameter, FloatParameterWithSlider, IntegerParameterWithSlider
from LegacyPipelineCreatorLib.PipelineBases import SinglePiecePipeline # Note: this import may show up as unused in linting, but it is needed for the exec calls to work

def _fixUpParameterName(parameterName):
  newName = parameterName.replace(" ", "")
  if not newName.isidentifier():
      raise Exception("Invalid name: '%s'" % newName)
  return newName

def _boolParamUI(param):
  return BooleanParameter(
    defaultValue=param.get('value', False))

def _doubleParamUI(param):
  return FloatParameterWithSlider(
    value=param.get('value', None),
    minimum=param.get('minimum', None),
    maximum=param.get('maximum', None),
    singleStep=param.get('singleStep', None),
    decimals=param.get('decimals', None))

def _integerParamUI(param):
  return IntegerParameterWithSlider(
    value=param.get('value', None),
    minimum=param.get('minimum', None),
    maximum=param.get('maximum', None),
    singleStep=param.get('singleStep', None))

def _enumParamUI(param):
  return StringComboBoxParameter(param['values'])

def _createParamUI(param):
  paramType = param['type']
  if paramType in ("float", "double"):
    return _doubleParamUI(param)
  elif paramType in ("int", "integer"):
    return _integerParamUI(param)
  elif paramType in ("enum"):
    return _enumParamUI(param)
  elif paramType in ("bool", "boolean"):
    return _boolParamUI(param)
  raise Exception("Error loading vtk filter json: Unknown parameter type '%s'" % paramType)

def _passThroughSetMethod(param):
  name = _fixUpParameterName(param['name'])
  def func(self, value):
    getattr(self._filter, "Set"+name)(value)
  return ("Set"+name, func)

def _enumParamSetMethod(param):
  name = _fixUpParameterName(param['name'])
  def func(self, value):
    getattr(self._filter, "Set%sTo%s" % (name, value.replace(' ', '')))()
  return ("Set"+name, func)

def _createParamSetMethod(param):
  paramType = param['type']
  if paramType in ("float", "double"):
    return _passThroughSetMethod(param)
  elif paramType in ("int", "integer"):
    return _passThroughSetMethod(param)
  elif paramType in ("enum"):
    return _enumParamSetMethod(param)
  elif paramType in ("bool", "boolean"):
    return _passThroughSetMethod(param)
  raise Exception("Error loading vtk filter json: Unknown parameter type '%s'" % paramType)

# Having the creation of the class in its own function is very important to
# making sure each call we get a brand new class and aren't overwriting anything
def _makeFilterClass(item):
  filtername = _fixUpParameterName(item['name'])
  parameterSetMethods = [_createParamSetMethod(p) for p in item['parameters']]

  classDefinition = textwrap.dedent('''
    class {filtername}PipelineWrapper(SinglePiecePipeline):
      @staticmethod
      def GetName():
        return '{name}'

      @staticmethod
      def GetDependencies():
        return []

      @staticmethod
      def GetInputType():
        return '{inputType}'

      @staticmethod
      def GetOutputType():
        return '{outputType}'

      @staticmethod
      def GetParameters():
        return {filtername}PipelineWrapper._GetParametersImpl()

      def __init__(self):
        super().__init__()
        self._filter = vtk.{filtername}()

      def _RunImpl(self, input):
        outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        self._filter.SetInputData(input.GetMesh())
        self._filter.Update()
        outputModel.SetAndObserveMesh(self._filter.GetOutput())
        return outputModel
    '''.format(
      name=item['name'],
      inputType=item['inputType'],
      outputType=item['outputType'],
      filtername=filtername,
    ))

  # We need the class to exist in the __main__ namespace so we can pickle it
  exec(classDefinition, globals(), globals())

  VTKFilter = globals()['%sPipelineWrapper' % filtername]

  # need the abstract method implementation to exist at class definition, so delegating
  # to a method that doesn't need to exists as class definition.
  # Note: this is probably not necessary in Python 3.10 via abc.update_abstractmethods
  @staticmethod
  def _GetParametersImpl():
    return [(p['name'], _createParamUI(p)) for p in item['parameters']]
  setattr(VTKFilter, "_GetParametersImpl", _GetParametersImpl)

  for methodName, method in parameterSetMethods:
    setattr(VTKFilter, methodName, method)

  return VTKFilter

def ReadFromFile(filename):
  """
  Reads a single json file and returns a class suitable for
  the pipeline creator.
  """

  with open(filename, 'r') as f:
    item = json.load(f)
  wrappedFilterClass = _makeFilterClass(item)
  return wrappedFilterClass

def ReadFromFolder(folder):
  """
  Reads all json files from given folder.
  Returns a list of classes suitable for the pipeline creator.
  """

  files = [x for x in os.listdir(folder) if x.endswith('.json')]
  classes = [ReadFromFile(os.path.join(folder, file)) for file in files]
  return classes

def RegisterLegacyPipelineModules(legacyPipelineCreatorLogic, folder):
  """
  Creates classes for all vtk filter json files in given folder and
  registers them with the pipeline creator.
  """

  classes = ReadFromFolder(folder)
  for c in classes:
    legacyPipelineCreatorLogic.registerModule(c)
