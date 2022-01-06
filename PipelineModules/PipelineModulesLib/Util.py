import re
import slicer

class ScopedNode(object):
  def __init__(self, node):
    self._node = node
  def __enter__(self):
    return self._node
  def __exit__(self, type, value, traceback):
    slicer.mrmlScene.RemoveNode(self._node)
    self._node = None

class ScopedDefaultStorageNode(object):
  def __init__(self, dataNode):
    self._storageNode = dataNode.CreateDefaultStorageNode()
  def __enter__(self):
    return self._storageNode
  def __exit__(self, type, value, traceback):
    self._storageNode.UnRegister(None)

def human_sorted(listlike):
  '''
  Sorts a list of strings with numbers like a human would
  abc1
  abc2
  ...
  abc9
  abc10
  abc11
  etc
  '''
  # https://nedbatchelder.com/blog/200712/human_sorting.html
  def keyFunc(s):
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', s)]
  return sorted(listlike, key=keyFunc)
