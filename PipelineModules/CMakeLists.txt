#-----------------------------------------------------------------------------
set(MODULE_NAME PipelineModules)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  PipelineModulesLib/PipelineParameters.py
  PipelineModulesLib/SegmentationsWrapping.py
  PipelineModulesLib/SegmentEditorWrapping.py
  PipelineModulesLib/SurfaceToolboxWrapping.py
  PipelineModulesLib/vtkFilterJSONReader.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui

  Resources/PipelineVTKFilterJSON/vtkConnectivityFilter.json
  Resources/PipelineVTKFilterJSON/vtkFillHolesFilter.json
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
