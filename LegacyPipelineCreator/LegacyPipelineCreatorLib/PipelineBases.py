import abc
import collections
from os import stat

PipelineProgress = collections.namedtuple("PipelineProgress",
  "progress currentPipelinePieceName currentPipelinePieceNumber numberOfPieces")

class PipelineInterface(abc.ABC):
  @staticmethod
  @abc.abstractmethod
  def GetName():
    pass

  @staticmethod
  @abc.abstractmethod
  def GetParameters():
    pass

  @staticmethod
  @abc.abstractmethod
  def GetInputType():
    pass

  @staticmethod
  @abc.abstractmethod
  def GetOutputType():
    pass

  @staticmethod
  @abc.abstractmethod
  def GetDependencies():
    pass

  @abc.abstractmethod
  def Run(self, inputNode):
    pass

  @abc.abstractmethod
  def SetProgressCallback(self, cb):
    pass

class ProgressablePipeline(PipelineInterface):
  def __init__(self):
    super().__init__()
    self._progressCallback = None

  def SetProgressCallback(self, cb):
      if (cb is not None and not callable(cb)):
        raise TypeError("cb is not callable or None")

      self._progressCallback = cb

  @staticmethod
  @abc.abstractmethod
  def GetNumberOfPieces():
    pass

  def _Progress(self, moduleName, currentPipelinePieceNumber):
    if self._progressCallback:
      self._progressCallback(PipelineProgress(
        progress=currentPipelinePieceNumber / self.GetNumberOfPieces(),
        currentPipelinePieceName=moduleName,
        currentPipelinePieceNumber=currentPipelinePieceNumber+1,
        numberOfPieces=self.GetNumberOfPieces(),
        ))

class SinglePiecePipeline(ProgressablePipeline):
  def __init__(self):
    ProgressablePipeline.__init__(self)

  @staticmethod
  def GetNumberOfPieces():
      return 1

  @abc.abstractmethod
  def _RunImpl(self, inputNode):
    pass

  def Run(self, inputNode):
    self._Progress(self.GetName(), 0)
    output = self._RunImpl(inputNode)
    self._Progress(self.GetName(), 1)
    return output
