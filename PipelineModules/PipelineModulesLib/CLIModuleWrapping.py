import collections
import enum
import re

import slicer

class BridgeParameterWrapper:
  '''
  The whole point of this class is to keep a reference to the factory as long as the brideParameter is alive
  since once the factory goes away, so does the bridgeParameter (in C++ land)
  '''
  def __init__(self, factory, bridgeParameter):
    self._factory = factory
    self._bridgeParameter = bridgeParameter
  def GetValue(self):
    return self._bridgeParameter.GetValue()
  def GetUI(self):
    return self._bridgeParameter.GetUI()

@enum.unique
class Channels(enum.Enum):
  Input = "input"
  Output = "output"
  NoneChannel = ""

def toChannelsEnum(channelString):
  if channelString.lower() == "input":
    return Channels.Input
  if channelString.lower() == "output":
    return Channels.Output
  if channelString == "":
    return Channels.NoneChannel
  raise Exception("Unknown channel: " + channelString)

CLIParameter = collections.namedtuple("CLIParameter",
  "name pipelineParameterName label tag channel ptype")

def getCLIParameters(cliNode):
  parameters = []
  for i in range(cliNode.GetNumberOfParameterGroups()):
    for j in range(cliNode.GetNumberOfParametersInGroup(i)):
      parameters.append(CLIParameter(
        name=cliNode.GetParameterName(i,j),
        pipelineParameterName=cliNode.GetParameterName(i,j).capitalize(),
        label=cliNode.GetParameterLabel(i,j),
        tag=cliNode.GetParameterTag(i,j),
        channel=toChannelsEnum(cliNode.GetParameterChannel(i,j)),
        ptype=cliNode.GetParameterType(i,j),
      ))
  return parameters

def isMRML(cliTag):
  return cliTag in ('geometry', 'image')

def cliParameterToMRMLType(cliParameter):
  disclaimer = "\n  This type may well be supported by CLI modules, but it may not be supported yet by CLI pipeline wrapping." \
    + " Please consider adding support."
  if cliParameter.tag == "geometry":
    if cliParameter.ptype in ("scalar", "model"):
      return "vtkMRMLModelNode"
    else:
      raise Exception("Unknown geometry type: " + cliParameter.ptype + disclaimer)
  elif cliParameter.tag == "image":
    if cliParameter.ptype == "label":
      return "vtkMRMLLabelMapVolumeNode"
    elif cliParameter.ptype == "scalar":
      return "vtkMRMLScalarVolumeNode"
    else:
      raise Exception("Unknown image type: " + cliParameter.ptype + disclaimer)
  else:
    raise Exception("Unknown tag: " + cliParameter.tag + disclaimer)
currentlyUnsupportedTags = [
  'point',
  'pointfile',
  'region',
  'table',
  'transform',
  'integer-enumeration',
  'float-enumeration',
  'double-enumeration',
  'string-enumeration',
  'file',
  'directory',
]

def checkForUnsupportedTags(cliNode, excludeArgs):
  for i in range(cliNode.GetNumberOfParameterGroups()):
    for j in range(cliNode.GetNumberOfParametersInGroup(i)):
      name = cliNode.GetParameterName(i,j)
      tag = cliNode.GetParameterTag(i,j)
      if name not in excludeArgs and tag in currentlyUnsupportedTags:
        raise Exception('PipelineCLI Attempting to use currently unsupported tag: ' + tag
          + '\nPlease consider adding support!')

def pipelineParameterName(s):
  return s.capitalize()

def cliToPipelineParameters(factory, cliParameters, excludeParameterNames=None):
  if excludeParameterNames is None:
    excludeParameterNames = ()
  if isinstance(excludeParameterNames, str):
    excludeParameterNames = (excludeParameterNames, )

  parameters = []
  for param in cliParameters:
    if not param.name in excludeParameterNames:
      paramWrapper = BridgeParameterWrapper(factory, factory.CreateParameterWrapper(param.name))
      if paramWrapper is None:
        raise Exception("Error paramWrapper should not be None. Did you load a module into the factory?")
      parameters.append((param.pipelineParameterName, param.label, paramWrapper))
  return parameters

_invalidCharactersRe = re.compile("[^a-zA-Z1-9_]")
def _fixupModuleName(name):
  return _invalidCharactersRe.sub('', name)
  
_pipelineClassTemplate = '''
class PipelineWrapper_{fixupModuleName}:
  @staticmethod
  def GetName():
    return '{moduleName}'

  @staticmethod
  def GetInputType():
    return '{inputType}'

  @staticmethod
  def GetOutputType():
    return '{outputType}'

  def __init__(self):
    self._parameters = dict()

  def Run(self, input):
    self.Set{inputParameter}(input)
    output = slicer.mrmlScene.AddNewNodeByClass(self.GetOutputType())
    output.CreateDefaultDisplayNodes()
    self.Set{outputParameter}(output)
    cliNode = slicer.cli.runSync(self.GetModule(), parameters=self._parameters)
    if cliNode.GetStatus() & cliNode.ErrorsMask:
      #error
      slicer.mrmlScene.RemoveNode(output)
      text = cliNode.GetErrorText()
      slicer.mrmlScene.RemoveNode(cliNode)
      raise Exception("CLI execution failed for "
        + self.GetModule().name + ": " + text)
    slicer.mrmlScene.RemoveNode(cliNode)
    return output
'''

def _deducePipelineRunArg(cliParameters, channel):
  options = [p for p in cliParameters
    if isMRML(p.tag) and p.channel == channel]
  if len(options) == 1:
    return options[0]
  raise Exception('Unable to deduce ' + str(channel) + ' argument: ' + str(options))

def getArgByName(cliParameters, name):
  return [p for p in cliParameters if p.name == name][0]

def PipelineCLI(cliModule, pipelineCreatorLogic, inputArgName=None, outputArgName=None, excludeArgs=None):
  excludeArgs = excludeArgs or []

  cliNode = slicer.cli.createNode(cliModule)
  checkForUnsupportedTags(cliNode, excludeArgs)

  cliParameters = getCLIParameters(cliNode)

  inputArg = getArgByName(cliParameters, inputArgName) if inputArgName else _deducePipelineRunArg(cliParameters, Channels.Input)
  outputArg = getArgByName(cliParameters, outputArgName) if outputArgName else _deducePipelineRunArg(cliParameters, Channels.Output)

  fixupModuleName = _fixupModuleName(cliModule.name)

  classDef = _pipelineClassTemplate.format(
    moduleName=cliModule.name,
    fixupModuleName=fixupModuleName,
    inputParameter=inputArg.pipelineParameterName,
    outputParameter=outputArg.pipelineParameterName,
    inputType=cliParameterToMRMLType(inputArg),
    outputType=cliParameterToMRMLType(outputArg),
  )

  # We need the class to exist in the __main__ namespace so we can pickle it
  exec(classDef, globals(), globals())

  cliPipeline = globals()['PipelineWrapper_%s' % fixupModuleName]

  @staticmethod
  def GetParameters():
    factory = slicer.qSlicerPipelineCLIModulesBridgeParameterFactory()
    factory.loadCLIModule(cliModule.name)
    return cliToPipelineParameters(factory, cliParameters, [inputArg.name, outputArg.name] + list(excludeArgs))
  setattr(cliPipeline, "GetParameters", GetParameters)

  dependencies = list(set(list(cliModule.dependencies) + ['PipelineCreator']))
  @staticmethod
  def GetDependencies():
    return dependencies
  setattr(cliPipeline, "GetDependencies", GetDependencies)

  @staticmethod
  def GetModule():
    return cliModule
  setattr(cliPipeline, "GetModule", GetModule)

  for param in cliParameters:
    def makeFunc(fparam):
      #returning a function from inside a function was necessary to get all the parameter stuff copied correctly
      def setFunc(self, value):
        self._parameters[fparam.name] = value
      return setFunc
    setattr(cliPipeline, "Set" + param.pipelineParameterName, makeFunc(param))

  pipelineCreatorLogic.registerModule(cliPipeline)
