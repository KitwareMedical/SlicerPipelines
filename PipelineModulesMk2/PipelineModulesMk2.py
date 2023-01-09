from slicer.ScriptedLoadableModule import *

#import all the default wrappings. doing the import will register them with the pipeline creator
from _PipelineModulesMk2 import (
    SurfaceToolboxWrapping,
)

#
# PipelineModulesMk2
#

class PipelineModulesMk2(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Pipeline ModulesMk2"
        self.parent.categories = ["Pipelines.Advanced"]
        self.parent.dependencies = ["PipelineCreatorMk2", "SegmentEditor", "Segmentations"]
        self.parent.contributors = ["Connor Bowley (Kitware, Inc.)"]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """
This module exists to create pipelines for the PipelineCreatorMk2 to use.
"""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = "This module was originally developed by Connor Bowley (Kitware, Inc.) for SlicerSALT."
        self.parent.hidden = True


#
# PipelineModulesMk2Logic
#

class PipelineModulesMk2Logic(ScriptedLoadableModuleLogic):
    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)
