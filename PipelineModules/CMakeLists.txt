#-----------------------------------------------------------------------------
set(MODULE_NAME PipelineModules)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  PipelineModulesLib/CLIModuleWrapping.py
  PipelineModulesLib/PipelineParameters.py
  PipelineModulesLib/SegmentationsWrapping.py
  PipelineModulesLib/SegmentEditorWrapping.py
  PipelineModulesLib/SurfaceToolboxWrapping.py
  PipelineModulesLib/Util.py
  PipelineModulesLib/VolumesWrapping.py
  PipelineModulesLib/vtkFilterJSONReader.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui

  Resources/PipelineVTKFilterJSON/vtkCleanPolyData.json
  Resources/PipelineVTKFilterJSON/vtkConnectivityFilter.json
  Resources/PipelineVTKFilterJSON/vtkDecimatePro.json
  Resources/PipelineVTKFilterJSON/vtkFillHolesFilter.json
  Resources/PipelineVTKFilterJSON/vtkPolyDataNormals.json
  Resources/PipelineVTKFilterJSON/vtkQuadricDecimation.json
  Resources/PipelineVTKFilterJSON/vtkSmoothPolyDataFilter.json
  Resources/PipelineVTKFilterJSON/vtkWindowedSincPolyDataFilter.json
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()
