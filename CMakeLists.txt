cmake_minimum_required(VERSION 3.13.4)

project(Pipelines)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/Pipelines")
set(EXTENSION_CATEGORY "Pipelines")
set(EXTENSION_CONTRIBUTORS "Connor Bowley (Kitware, Inc.)")
set(EXTENSION_DESCRIPTION "This extension is used for creating Pipelines")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/Pipelines.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/Pipelines/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(PipelineCreator)
add_subdirectory(PipelineModules)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
