cmake_minimum_required(VERSION 3.13.4)

project(Pipelines)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/KitwareMedical/SlicerPipelines/blob/main/README.md")
set(EXTENSION_CATEGORY "Pipelines")
set(EXTENSION_CONTRIBUTORS "Connor Bowley (Kitware, Inc.)")
set(EXTENSION_DESCRIPTION "SlicerPipelines is an extension for 3D Slicer that offers the ability to create simple modules (aka pipelines) via a GUI interface with no coding knowledge needed")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/KitwareMedical/SlicerPipelines/main/Pipelines.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/KitwareMedical/SlicerPipelines/main/Screenshots/1.png https://raw.githubusercontent.com/KitwareMedical/SlicerPipelines/main/Screenshots/2.png https://raw.githubusercontent.com/KitwareMedical/SlicerPipelines/main/Screenshots/3.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(LegacyPipelineCreator)
add_subdirectory(LegacyPipelineModules)
add_subdirectory(LegacyPipelineCLIBridge)
add_subdirectory(LegacyPipelineCaseIterator)
add_subdirectory(PipelineCreator)
add_subdirectory(PipelineModules)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
