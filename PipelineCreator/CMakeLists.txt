#-----------------------------------------------------------------------------
set(MODULE_NAME PipelineCreator)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py

  _${MODULE_NAME}/PipelineRegistrar.py

  _${MODULE_NAME}/PipelineCreation/__init__.py
  _${MODULE_NAME}/PipelineCreation/core.py
  _${MODULE_NAME}/PipelineCreation/util.py
  _${MODULE_NAME}/PipelineCreation/validation.py

  _${MODULE_NAME}/PipelineCreation/CodeGeneration/__init__.py
  _${MODULE_NAME}/PipelineCreation/CodeGeneration/cmakelists.py
  _${MODULE_NAME}/PipelineCreation/CodeGeneration/logic.py
  _${MODULE_NAME}/PipelineCreation/CodeGeneration/module.py
  _${MODULE_NAME}/PipelineCreation/CodeGeneration/parameterNode.py
  _${MODULE_NAME}/PipelineCreation/CodeGeneration/util.py
  _${MODULE_NAME}/PipelineCreation/CodeGeneration/widget.py

  Widgets/PipelineListWidget.py
  Widgets/PipelineProgressBar.py
  Widgets/SelectPipelinePopUp.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/Icons/${MODULE_NAME}_template_icon.png
  Resources/UI/${MODULE_NAME}.ui
  Resources/UI/SelectPipelinePopUp.ui
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
