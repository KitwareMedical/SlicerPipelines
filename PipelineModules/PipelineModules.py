from slicer.ScriptedLoadableModule import *

#import all the default wrappings. doing the import will register them with the pipeline creator
from _PipelineModules import (
    SegmentationsWrapping,
    SegmentEditorWrapping,
    SurfaceToolboxWrapping,
    vtkWrapping,
)

#
# PipelineModules
#

class PipelineModules(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Pipeline Modules"
        self.parent.categories = ["Pipelines.Advanced"]
        self.parent.dependencies = ["PipelineCreator", "SegmentEditor", "Segmentations"]
        self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
        self.parent.helpText = """
This module exists to create pipelines for the PipelineCreator to use.
"""
        self.parent.acknowledgementText = "This module was originally developed by Connor Bowley (Kitware, Inc.) for SlicerSALT."
        self.parent.hidden = True


#
# PipelineModulesLogic
#

class PipelineModulesLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)
