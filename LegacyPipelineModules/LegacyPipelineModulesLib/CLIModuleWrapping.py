import collections
import enum
import re
from LegacyPipelineModulesLib.Util import ScopedNode

import slicer
import vtk
from LegacyPipelineCreatorLib.PipelineBases import SinglePiecePipeline # Note: this import may show up as unused in linting, but it is needed for the exec calls to work
from LegacyPipelineCreator import CallAfterAllTheseModulesLoaded, LegacyPipelineCreatorLogic

class BridgeParameterWrapper:
  '''
  The whole point of this class is to delete the bridgeParameter (which was returned from C++ land
  as an owning pointer) when we are done with it
  '''
  def __init__(self, bridgeParameter):
    self._bridgeParameter = bridgeParameter
  def __del__(self):
    self._bridgeParameter.deleteThis()
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
  "name pipelineParameterName label tag channel ptype multiple")

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
        multiple=cliNode.GetParameterMultiple(i,j).lower() in ('true', '1'),
      ))
  return parameters

def isMRML(cliTag):
  return cliTag in ('geometry', 'image')

def cliParameterToMRMLType(cliParameter):
  disclaimer = "\n  This type may well be supported by CLI modules, but it may not be supported yet by CLI pipeline wrapping." \
    + " Please consider adding support."
  if cliParameter.tag == "geometry":
    if cliParameter.ptype in ("scalar", "model"):
      if cliParameter.multiple: # no way to do "and cliParameter.aggregate"
        return "vtkMRMLModelHierarchyNode"
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
      paramWrapper = BridgeParameterWrapper(factory.CreateParameterWrapper(param.name))
      if paramWrapper is None:
        raise Exception("Error paramWrapper should not be None. Did you load a module into the factory?")
      parameters.append((param.pipelineParameterName, param.label, paramWrapper))
  return parameters

_invalidCharactersRe = re.compile("[^a-zA-Z1-9_]")
def _fixupModuleName(name):
  return _invalidCharactersRe.sub('', name)

#if this name changes, change parentClass in PipelineCLI
class DefaultOutputCLI(SinglePiecePipeline):
  def __init__(self):
    super().__init__()

  def _RunImpl(self, input):
    self._SetInput(input)
    output = slicer.mrmlScene.AddNewNodeByClass(self.GetOutputType())
    if output.IsA('vtkMRMLDisplayableNode'):
      output.CreateDefaultDisplayNodes()
    self._SetOutput(output)
    with ScopedNode(slicer.cli.runSync(self.GetModule(), parameters=self._parameters)) as cliNode:
      if cliNode.GetStatus() & cliNode.ErrorsMask:
        #error
        text = cliNode.GetErrorText()
        raise Exception("CLI execution failed for "
          + self.GetModule().name + ": " + text)
    return output

#if this name changes, change parentClass in PipelineCLI
class ModelHierarchyOutputCLI(SinglePiecePipeline):
  def __init__(self):
    super().__init__()
    self._hierarchyName = None

  def _nameExists(self, name):
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    sceneItemID = shNode.GetSceneItemID()
    return any([
      slicer.mrmlScene.GetNodesByName(name).GetNumberOfItems() > 0,
      shNode.GetItemChildWithName(sceneItemID, name) != 0,
    ])

  def _RunImpl(self, input):
    '''
    When a CLI modules has a model hierarchy as its output, the model hierarchy is imported into the
    scene, which will delete the model hierarchy node and put all of its models into a subject
    hierarchy folder with the same name the model hierarchy had.

    So we create the model hierarchy with a name that is completely unique, then after the cli run
    we find the subject hierarchy folder with that name and grab the first model out of it.
    '''
    if self.GetOutputType() != 'vtkMRMLModelNode':
      raise Exception("Unable to run model hierarchy output CLI that doesn't have model as output")

    self._SetInput(input)
    modelHierarchy = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelHierarchyNode')
    basename = self.GetName() + "Models"
    self._hierarchyName = basename
    index = 0
    while self._nameExists(self._hierarchyName):
      index += 1
      self._hierarchyName = basename + str(index)

    modelHierarchy.SetName(self._hierarchyName)
    self._SetOutput(modelHierarchy)

    with ScopedNode(slicer.cli.runSync(self.GetModule(), parameters=self._parameters)) as cliNode:
      if cliNode.GetStatus() & cliNode.ErrorsMask:
        #error
        slicer.mrmlScene.RemoveNode(modelHierarchy)
        text = cliNode.GetErrorText()
        raise Exception("CLI execution failed for "
          + self.GetModule().name + ": " + text)

    # get output model
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    sceneItemID = shNode.GetSceneItemID()
    modelsFolderId = shNode.GetItemChildWithName(sceneItemID, self._hierarchyName)
    if modelsFolderId == 0:
      raise Exception(self.GetName() + ": Unable to find created models")

    children = vtk.vtkIdList()
    shNode.GetItemChildren(modelsFolderId, children)
    if children.GetNumberOfIds() == 0:
      raise Exception(self.GetName() + ": No models were created")

    outputShId = children.GetId(0)

    slicer.mrmlScene.RemoveNode(modelHierarchy) # this is unnecessary as of this writing, but adding for future safety
    shNode.SetItemParent(outputShId, shNode.GetItemParent(modelsFolderId))

    shNode.RemoveItem(modelsFolderId)

    return shNode.GetItemDataNode(outputShId)

_pipelineClassTemplate = '''
class PipelineWrapper_{fixupModuleName}({parentClass}):
  @staticmethod
  def GetName():
    return '{moduleName}'

  @staticmethod
  def GetInputType():
    return '{inputType}'

  @staticmethod
  def GetOutputType():
    return '{outputType}'

  @staticmethod
  def GetParameters():
    return PipelineWrapper_{fixupModuleName}._GetParametersImpl()

  @staticmethod
  def GetDependencies():
    return PipelineWrapper_{fixupModuleName}._GetDependenciesImpl()

  def __init__(self):
    super().__init__()
    self._parameters = dict()

  def _SetInput(self, input):
    self.Set{inputParameter}(input)

  def _SetOutput(self, output):
    self.Set{outputParameter}(output)
'''

def _deducePipelineRunArg(cliParameters, channel):
  options = [p for p in cliParameters
    if isMRML(p.tag) and p.channel == channel]
  if len(options) == 1:
    return options[0]
  raise Exception('Unable to deduce ' + str(channel) + ' argument: ' + str(options))

def getArgByName(cliParameters, name):
  return [p for p in cliParameters if p.name == name][0]

def PipelineCLINow(cliModule, legacyPipelineCreatorLogic=None, inputArgName=None, outputArgName=None, excludeArgs=None):
  if isinstance(cliModule, str):
    cliModule = slicer.app.moduleManager().module(cliModule)

  legacyPipelineCreatorLogic = legacyPipelineCreatorLogic or LegacyPipelineCreatorLogic()
  excludeArgs = excludeArgs or []

  cliNode = slicer.cli.createNode(cliModule)
  checkForUnsupportedTags(cliNode, excludeArgs)

  cliParameters = getCLIParameters(cliNode)

  inputArg = getArgByName(cliParameters, inputArgName) if inputArgName else _deducePipelineRunArg(cliParameters, Channels.Input)
  outputArg = getArgByName(cliParameters, outputArgName) if outputArgName else _deducePipelineRunArg(cliParameters, Channels.Output)

  fixupModuleName = _fixupModuleName(cliModule.name)

  parentClass = "DefaultOutputCLI"
  outputType = cliParameterToMRMLType(outputArg)

  if outputType == "vtkMRMLModelHierarchyNode":
    parentClass = "ModelHierarchyOutputCLI"
    outputType = "vtkMRMLModelNode"

  classDef = _pipelineClassTemplate.format(
    moduleName=cliModule.name,
    fixupModuleName=fixupModuleName,
    inputParameter=inputArg.pipelineParameterName,
    outputParameter=outputArg.pipelineParameterName,
    inputType=cliParameterToMRMLType(inputArg),
    outputType=outputType,
    parentClass=parentClass
  )

  # We need the class to exist in the __main__ namespace so we can pickle it
  exec(classDef, globals(), globals())

  cliPipeline = globals()['PipelineWrapper_%s' % fixupModuleName]

  # need the abstract method implementation to exist at class definition, so delegating
  # to a method that doesn't need to exists as class definition.
  # Note: this is probably not necessary in Python 3.10 via abc.update_abstractmethods
  @staticmethod
  def _GetParametersImpl():
    factory = slicer.qSlicerPipelineCLIModulesBridgeParameterFactory()
    factory.loadCLIModule(cliModule.name)
    return cliToPipelineParameters(factory, cliParameters, [inputArg.name, outputArg.name] + list(excludeArgs))
  setattr(cliPipeline, "_GetParametersImpl", _GetParametersImpl)

  dependencies = list(set(list(cliModule.dependencies) + ['LegacyPipelineCreator']))
  @staticmethod
  def _GetDependenciesImpl():
    return dependencies
  setattr(cliPipeline, "_GetDependenciesImpl", _GetDependenciesImpl)

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

  legacyPipelineCreatorLogic.registerModule(cliPipeline)

# Recommended use:
#
# try:
#   from LegacyPipelineModulesLib.CLIModuleWrapping import PipelineCLI
#   PipelineCLI("MeshToLabelMap", inputArgName="mesh", excludeArgs=['reference'])
# except ImportError:
#   pass
def PipelineCLI(cliModuleName, legacyPipelineCreatorLogic=None, inputArgName=None, outputArgName=None, excludeArgs=None):
  def f():
    PipelineCLINow(
      slicer.app.moduleManager().module(cliModuleName),
      legacyPipelineCreatorLogic,
      inputArgName,
      outputArgName,
      excludeArgs)
  CallAfterAllTheseModulesLoaded(f, ["LegacyPipelineCreator", cliModuleName])
