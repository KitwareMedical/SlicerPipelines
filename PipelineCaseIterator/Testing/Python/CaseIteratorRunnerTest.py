import unittest
import os
import typing

from PipelineCaseIterator import PipelineCaseIteratorRunner
from PipelineCaseIterator import rowToTypes
import slicer
from SampleData import SampleDataLogic


class RowToTypesTest(unittest.TestCase):

    def setUp(self) -> None:
        self.sampleData = SampleDataLogic()
        self.sampleData.downloadSample('MRHead')
        destFolderPath = slicer.mrmlScene.GetCacheManager().GetRemoteCacheDirectory()
        self.testFileName = os.path.join(destFolderPath, 'MR-head.nrrd')
        slicer.mrmlScene.Clear()

    def tearDown(self) -> None:
        slicer.mrmlScene.Clear()

    def testSimpleRowToTypes(self):
        row = {"a": "1", "b": "2", "node": self.testFileName }
        types = {"a": str, "b": int, "node": slicer.vtkMRMLScalarVolumeNode }
        data, nodes = rowToTypes(row, types)
        self.assertEquals(data["a"], "1")
        self.assertEquals(data["b"], 2)
        self.assertEquals(len(nodes), 1)
        nodeCount = slicer.mrmlScene.GetNodesByClass('vtkMRMLScalarVolumeNode').GetNumberOfItems()
        self.assertEquals(nodeCount, 1)

    def testConversionError(self):
        row = {"a": "1", "b": "this is no int", "node": self.testFileName }
        types = {"a": str, "b": int, "node": slicer.vtkMRMLScalarVolumeNode }
        data, nodes = rowToTypes(row, types)
        self.assertEquals(data, None)
        self.assertEquals(nodes, None)
        nodeCount = slicer.mrmlScene.GetNodesByClass('vtkMRMLScalarVolumeNode').GetNumberOfItems()
        self.assertEquals(nodeCount, 0)

    def testLoadingError(self):
        row = {"a": "1", "b": "2", "node": "filedoesnotexist.nrrd" }
        types = {"a": str, "b": int, "node": slicer.vtkMRMLScalarVolumeNode }
        data, nodes = rowToTypes(row, types)
        self.assertEquals(data, None)
        self.assertEquals(nodes, None)
        nodeCount = slicer.mrmlScene.GetNodesByClass('vtkMRMLScalarVolumeNode').GetNumberOfItems()
        self.assertEquals(nodeCount, 0)


if __name__ == '__main__':
    unittest.main()