#!/usr/bin/env python-real
import argparse
import sys
import traceback
from PipelineCaseIterator import PipelineCaseIteratorRunner

_progressStatement = '<pipelineProgress>{totalProgress}, {currentPipelinePieceName}, {currentPipelinePieceNumber}, {numberOfPieces}</pipelineProgress>'


def _onProgress(totalProgress: float,
                currentPipelinePieceName: str,
                currentPipelinePieceNumber: int,
                numberOfPieces: int):
  """Note this is inner callback to a PipelineProgressObject callback"""
  print(_progressStatement.format(
    totalProgress=int(totalProgress * 100),
    currentPipelinePieceName=currentPipelinePieceName,
    currentPipelinePieceNumber=currentPipelinePieceNumber,
    numberOfPieces=numberOfPieces,
  ))

class _Namespace(object):
  pass

def cleanupQuotes(args):
  newArgs = _Namespace()
  for key, value in args.__dict__.items():
    if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
      newArgs.__dict__[key] = value[1:-1]
    else:
      newArgs.__dict__[key] = value
  return newArgs


def main(args):
  runner = PipelineCaseIteratorRunner(
    args.pipelineName,
    args.inputFile,
    args.outputDirectory,
    resultsFileName=args.resultsFileName,
    prefix=args.prefix,
    suffix=args.suffix,
    timestampFormat=args.timestampFormat)

  runner.setProgressCallback(_onProgress)
  runner.run()

if __name__ == "__main__":

  parser = argparse.ArgumentParser()
  parser.add_argument('--inputFile', required=True)
  parser.add_argument('--outputDirectory', required=True)
  parser.add_argument('--pipelineName', required=True)
  parser.add_argument('--prefix', required=False, default=None)
  parser.add_argument('--suffix', required=False, default=None)
  parser.add_argument('--timestampFormat', required=False, default=None)
  parser.add_argument('--resultsFileName', required=False, default='results.csv')


  try:
    args = parser.parse_args()
    args = cleanupQuotes(args)
    main(args)
    sys.exit(0)
  except Exception as e:
    print(str(e) + '\n\n' + "".join(traceback.TracebackException.from_exception(e).format()))
    sys.exit(1)
