import threading
import time

import qt

class Asynchrony(object):
  '''
  This class allows for functions to be run in other threads. It's unique contribution to the plethora
  of threading libraries around is it is designed to work with 3D Slicer's use of Qt and its event loop.

  This class takes care of causing the main Qt event loop thread to yield the Python GIL allowing the
  newly spawned thread to run. It is the job of the function being run to yield control enough to allow
  the Qt GUI to still be responsive.
  Note: it is not advised to spawn Asynchronies from inside other Asynchronies
  '''

  class CancelledException(Exception):
    '''
    This exception is raised if the user cancels a running Asynchrony
    '''
    pass

  class _PerThreadCrossThreadStorage(object):
    def __init__(self):
      self.cancelled = False
  _CrossThreadStorage = {}
  _ThreadLocalStorage = threading.local()

  @staticmethod
  def YieldGIL(seconds=0):
    '''
    Yields the Global Interpreter Lock for the given time.
    Blocks the thread it is called from.
    May be called from any thread.
    '''
    time.sleep(seconds)

  @staticmethod
  def RunOnMainThread(function):
    '''
    Runs a function on the main thread, blocking until it returns.
    May only be called from newly started thread (i.e. from inside the function passed to Asynchrony object).
    If you call this function from the main thread, it will block indefinitely.

    If "f()" returns a value, "RunOnMainThread(f)" will return the same value
    If "f()" raises an Exception, "RunOnMainThread(f)" will raise the same Exception
    Note: the passed in function need not return a value
    This method is intended to allow other threads to "run" any operation that requires updating the GUI
    (e.g. update a progress bar). Because this runs on the main Qt thread, if long running operations are
    called, it may cause the GUI to become unresponsive.
    '''
    if not callable(function):
      raise Exception('Expected callable in Asynchrony.RunOnMainThread')

    returnVal = []
    exception = []
    def wrapper():
      #even if function doesn't return, it will "return" None
      try:
        returnVal.append(function())
      except Exception as e:
        exception.append(e)

    Asynchrony._ThreadLocalStorage.mainQueue.append(wrapper)
    while not returnVal and not exception:
      Asynchrony.YieldGIL()
    if exception:
      raise exception[0]
    return returnVal[0]

  @staticmethod
  def IsCancelled():
    '''
    Returns True if asynchrony was cancelled.
    May only be called from newly started thread (i.e. from inside the function passed to Asynchrony object).
    '''
    Asynchrony.YieldGIL()
    return Asynchrony._CrossThreadStorage[threading.get_ident()].cancelled

  @staticmethod
  def CheckCancelled():
    '''
    Raises an exception if asynchrony was cancelled.
    May only be called from newly started thread (i.e. from inside the function passed to Asynchrony object).
    '''
    if Asynchrony.IsCancelled():
      raise Asynchrony.CancelledException('Asynchrony was cancelled')

  def __init__(self, func, finishCallback=None):
    '''
    Creates a new Asynchrony object.
    func - The function to call.
    finishCallback - A callback to call when the Asynchrony is finished. Will be called
        from the original calling thread

    A new Asynchrony should only be created from the main thread (the one that runs the Qt GUI)

    The passed in function "func" must:
     - Not do any operations that update the Qt GUI, unless they are run through Asynchrony.RunOnMainThread.
       Doing so will cause the program to crash.
    The passed in function "func" should:
     - yield the GIL periodically using either Asynchrony.YieldGIL() or another function that yields the GIL
       (e.g. io bound operations such as pipe reads, some numpy operations also yield the GIL)
     - periodically call Asynchrony.CheckCancelled() or Asynchrony.IsCancelled() to respond to cancel requests
    The passed in function "func" may:
     - raise an exception
     - return a value
    '''
    self._finishCallback = finishCallback
    self._func = func

    self._thread = None
    self._finished = False

    self._output = None
    self._exception = None
    self._mainQueue = []

  def Start(self):
    '''
    Starts the Asynchrony

    A new thread is spawned that the passed in function is run on.
    A QTimer is started on the calling thread that will periodically yield control to the new thread
    as well as run any queued functions
    '''
    if self._thread is not None:
      raise Exception('AsyncPipelineRunner is already running')

    self._thread = threading.Thread(target=lambda: self._Run(self._func))
    self._thread.start()
    Asynchrony._CrossThreadStorage[self._thread.ident] = Asynchrony._PerThreadCrossThreadStorage()
    qt.QTimer.singleShot(0, self._MainThreadQueueMain)

  def Cancel(self):
    '''
    Cancels a running Asynchrony.

    This causes the function
    '''
    Asynchrony._CrossThreadStorage[self._thread.ident].cancelled = True

  def GetOutput(self):
    '''
    Gets the output from the passed in function.

    Raises an Exception if the function has not finished running.
    If the function raised an exception, this will raise the same exception.

    Note: If the passed in function does not return a value, this should still
          be called to see if an exception was thrown.
    '''
    if not self._finished:
      raise Exception("Cannot get output from unfinished run")
    if self._exception is not None:
      raise self._exception
    return self._output

  def _Run(self, func):
    '''
    Private implementation function.

    This function wraps the passed in function and takes care of thread setup
    and exception handling
    '''
    #shallow copy the mainQueue list to thread local storage so when the
    #thread local storage gets updated it updates the class member
    Asynchrony._ThreadLocalStorage.mainQueue = self._mainQueue

    #wait until cross thread storage is setup by the caller thread to start going
    while not threading.get_ident() in Asynchrony._CrossThreadStorage:
      self.YieldGIL(0.01)

    try:
      self._Finish(output=func())
    except Exception as e:
      self._Finish(exception=e)

  def _Finish(self, output=None, exception=None):
    '''
    Private implementation function.

    Sets output and/or exception and signals timer loop to stop and join the thread
    '''
    self._output = output
    self._exception = exception
    self._finished = True

  def _MainThreadQueueMain(self):
    '''
    Private implementation function.

    Pulled heavily from SimpleITK/SimpleFilters
    https://github.com/SimpleITK/SlicerSimpleFilters/blob/92e8db0030f6f9d9ea99dd5d8d1425b6b2189a68/SimpleFilters/SimpleFilters.py#L468

    This is magic to make the whole thing work. This is where we run functions that have to be
    run on the main thread and also where we cause the main thread to yield control to the other
    thread. When we are finished, this is also what causes the finish callback to get called and
    the thread to be joined.

    If we are not finished we call this again.
    '''
    try:
      while self._mainQueue:
        function = self._mainQueue.pop(0)
        function()
      self.YieldGIL(0.01)
      if not self._finished:
        qt.QTimer.singleShot(0, self._MainThreadQueueMain)
      else:
        if self._finishCallback:
          self._finishCallback()
        qt.QTimer.singleShot(0, self._Join)
    except Exception as e:
      import sys
      sys.stderr.write("Exception caught in Asynchrony._MainThreadQueueMain")

      #attempt to keep going
      qt.QTimer.singleShot(0, self._MainThreadQueueMain)

  def _Join(self):
    '''
    Private implementation function.

    Note to maintainers, only call this after _Finish has been called and
    we are done with cross thread storage
    '''
    Asynchrony._CrossThreadStorage.pop(self._thread.ident, None)
    self._thread.join()
