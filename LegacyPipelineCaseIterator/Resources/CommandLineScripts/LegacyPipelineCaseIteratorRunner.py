#!/usr/bin/env python-real
import argparse
import sys
import traceback
from LegacyPipelineCaseIterator import LegacyPipelineCaseIteratorRunner

_progressStatement = '<pipelineProgress>{overallPercent}, {currentPipelinePercent}, {totalCount}, {currentNumber}</pipelineProgress>'

def _onProgress(progress):
  print (_progressStatement.format(
    overallPercent=progress.overallPercent,
    currentPipelinePercent=progress.currentPipelinePercent,
    totalCount=progress.totalCount,
    currentNumber=progress.currentNumber,
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
  runner = LegacyPipelineCaseIteratorRunner(
    args.pipelineName,
    args.inputDirectory,
    args.outputDirectory,
    outputExtension=args.outputExtension,
    prefix=args.prefix,
    suffix=args.suffix,
    timestampFormat=args.timestampFormat)

  runner.setProgressCallback(_onProgress)
  runner.run()

if __name__ == "__main__":

  parser = argparse.ArgumentParser()
  parser.add_argument('--inputDirectory', required=True)
  parser.add_argument('--outputDirectory', required=True)
  parser.add_argument('--pipelineName', required=True)
  parser.add_argument('--prefix', required=False, default=None)
  parser.add_argument('--suffix', required=False, default=None)
  parser.add_argument('--outputExtension', required=False, default=None)
  parser.add_argument('--timestampFormat', required=False, default=None)


  try:
    args = parser.parse_args()
    args = cleanupQuotes(args)
    main(args)
    sys.exit(0)
  except Exception as e:
    print(str(e) + '\n\n' + "".join(traceback.TracebackException.from_exception(e).format()))
    sys.exit(1)
