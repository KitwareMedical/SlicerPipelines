#-----------------------------------------------------------------------------
set(MODULE_NAME LegacyPipelineCreator)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  Widgets/SelectModulePopUp.py
  Widgets/PipelineModuleListWidget.py

  LegacyPipelineCreatorLib/_Private/ModuleTemplate.py
  LegacyPipelineCreatorLib/PipelineBases.py
  LegacyPipelineCreatorLib/Asynchrony.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui

  Resources/PipelineTemplateModule/CMakeLists.txt.template
  Resources/PipelineTemplateModule/XXX.py.template
  Resources/PipelineTemplateModule/CommandLineScripts/RunXXX.py.template
  Resources/PipelineTemplateModule/Resources/Icons/XXX.png
  Resources/PipelineTemplateModule/Resources/UI/XXX.ui
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
