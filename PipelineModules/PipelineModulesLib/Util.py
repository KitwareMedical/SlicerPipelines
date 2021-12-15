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
