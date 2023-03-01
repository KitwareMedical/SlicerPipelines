import typing

import qt
import slicer

from slicer.parameterNodeWrapper import unannotatedType

class PipelineProgressCallback:
    """
    Special class for getting progress reports for pipelines.

    Is a class for ease in determining if a parameter is a pipeline progress callback.
    """
    def __init__(self, cb=None):
        """
        cb is a callable that takes 4 args,
            (totalProgress, currentPipelinePieceName, currentPipelinePieceNumber, numberOfPieces)
        """
        self._cb = cb
        self.totalProgress: float = 0.0
        self.currentPipelinePieceName: str = ""
        self.currentPipelinePieceNumber: int = 0
        self.numberOfPieces: int = 0

    def setCallback(self, cb):
        """
        cb is a callable that takes 4 args,
            (totalProgress, currentPipelinePieceName, currentPipelinePieceNumber, numberOfPieces)
        """
        self._cb = cb

    def reportProgress(self,
                       currentPipelinePieceName: str,
                       pieceProgress: float,
                       currentPipelinePieceNumber: int,
                       numberOfPieces: int) -> None:
        """
        Updates the progress report and calls the callback, if any is set.
        """
        perPieceVal = 1.0 / numberOfPieces
        self.totalProgress = perPieceVal * currentPipelinePieceNumber + perPieceVal * pieceProgress
        self.currentPipelinePieceName = currentPipelinePieceName
        self.currentPipelinePieceNumber = currentPipelinePieceNumber
        self.numberOfPieces = numberOfPieces

        if self._cb is not None:
            self._cb(self.totalProgress, self.currentPipelinePieceName, self.currentPipelinePieceNumber, self.numberOfPieces)

    def getSubCallback(self, pieceNumber, numberOfPieces) -> "PipelineProgressCallback":
        """
        Used to get a fine grained callback for a particular piece of a pipeline.
        """
        def cb(totalSubProgress, currentPipelinePieceName, currentPipelineSubPieceNumber, numberOfSubPieces):
            self.reportProgress(currentPipelinePieceName, totalSubProgress, pieceNumber, numberOfPieces)
        return PipelineProgressCallback(cb)


def isPipelineProgressCallback(param):
    """
    Determines if a type is a possibly Optional PipelineProgressCallback.
    """
    param = unannotatedType(param)
    args = typing.get_args(param)
    # remove Optional if it exists
    if typing.get_origin(param) == typing.Union and len(args) == 2 and args[1] == type(None):
        param = typing.get_args(param)[0]
    return unannotatedType(param) == PipelineProgressCallback

class PipelineProgressBar(qt.QWidget):
    """
    Widget that is a special progress bar for pipeline progress.

    Shows extra information like the current pipeline name.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(qt.QVBoxLayout())
        self._progressBar = qt.QProgressBar()
        self._progressBar.maximum = 100
        self.layout().addWidget(self._progressBar)

    def getProgressCallback(self) -> PipelineProgressCallback:
        return PipelineProgressCallback(self.setProgress)

    def setProgress(self, totalProgress: float, currentPipelinePieceName: str, currentPipelinePieceNumber: int, numberOfPieces: int):
        self._progressBar.value = int(totalProgress * 100)
        name = f"{currentPipelinePieceName} " if currentPipelinePieceName != "" else ""
        self._progressBar.setFormat(f"%p% ({name}{currentPipelinePieceNumber}/{numberOfPieces})")
        # need to process events so it updates on the screen.
        slicer.app.processEvents()

