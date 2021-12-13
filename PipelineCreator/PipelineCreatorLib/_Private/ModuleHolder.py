import inspect

class ModuleHolder:
  def __init__(self, module = None):
    self._module = module

  @property
  def name(self):
    try:
      return self._module.GetName()
    except TypeError:
      return self._module().GetName()

  @property
  def inputType(self):
    try:
      return self._module.GetInputType()
    except TypeError:
      return self._module().GetInputType()

  @property
  def outputType(self):
    try:
      return self._module.GetOutputType()
    except TypeError:
      return self._module().GetOutputType()

  @property
  def dependencies(self):
    try:
      return self._module.GetDependencies()
    except TypeError:
      return self._module().GetDependencies()

  @property
  def moduleClass(self):
    return self._module if inspect.isclass(self._module) else self._module.__class__

  def moduleInstance(self):
    return self._module if not inspect.isclass(self._module) else self._module()

  def MakeParameters(self):
    try:
      return self._module.GetParameters()
    except TypeError:
      return self._module().GetParameters()

  def updateParameterNodeFromSelf(self, param):
    param.SetParameter('name', self.name)
    param.SetParameter('inputType', self.inputType)
    param.SetParameter('outputType', self.outputType)
    #TODO: implement this

  def updateSelfFromParameterNode(self, param):
    #TODO: implement this
    pass

  def __str__(self) -> str:
    return self.name

  def __repr__(self):
    return self.__str__()
