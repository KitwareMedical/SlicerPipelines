cmake_minimum_required(VERSION 3.13.4)

project(Pipelines)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/KitwareMedical/SlicerPipelines/wiki")
set(EXTENSION_CATEGORY "Pipelines")
set(EXTENSION_CONTRIBUTORS "Connor Bowley (Kitware, Inc.)")
set(EXTENSION_DESCRIPTION "SlicerPipelines is an extension for 3D Slicer that offers the ability to create simple modules (aka pipelines) via a GUI interface with no coding knowledge needed")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/Pipelines.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/KitwareMedical/SlicerPipelines/main/Screenshots/1.png https://raw.githubusercontent.com/KitwareMedical/SlicerPipelines/main/Screenshots/2.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(PipelineCreator)
add_subdirectory(PipelineModules)
add_subdirectory(PipelineCLIBridge)
add_subdirectory(PipelineCaseIterator)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
