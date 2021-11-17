project(qSlicer${MODULE_NAME}ModuleWidgets)

find_package(SlicerExecutionModel REQUIRED ModuleDescriptionParser)

macro(ConfigureBridge name underlying_type tag)
  set(BRIDGE_TEMPLATE_NAME ${name})
  set(BRIDGE_TEMPLATE_TYPE ${underlying_type})
  set(BRIDGE_TEMPLATE_TAG ${tag})
  configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/qSlicerPipelineCLIModulesConcreteBridgeParameter.h.template
    ${CMAKE_CURRENT_BINARY_DIR}/${name}.h
    @ONLY
  )
  configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/qSlicerPipelineCLIModulesConcreteBridgeParameter.cxx.template
    ${CMAKE_CURRENT_BINARY_DIR}/${name}.cxx
    @ONLY
  )
endmacro()

ConfigureBridge(qSlicerPipelineCLIModulesIntegerBridgeParameter int integer)
ConfigureBridge(qSlicerPipelineCLIModulesFloatBridgeParameter float float)
ConfigureBridge(qSlicerPipelineCLIModulesDoubleBridgeParameter double double)
ConfigureBridge(qSlicerPipelineCLIModulesBooleanBridgeParameter bool boolean)
ConfigureBridge(qSlicerPipelineCLIModulesStringBridgeParameter QString string)
ConfigureBridge(qSlicerPipelineCLIModulesIntegerVectorBridgeParameter std::vector<int> integer-vector)
ConfigureBridge(qSlicerPipelineCLIModulesFloatVectorBridgeParameter std::vector<float> float-vector)
ConfigureBridge(qSlicerPipelineCLIModulesDoubleVectorBridgeParameter std::vector<double> double-vector)

#having issues with using std::vector<QString> or QVector<QString> as a return from C++ to Python.
#will be returned as a comma separated string
ConfigureBridge(qSlicerPipelineCLIModulesStringVectorBridgeParameter QString string-vector)

set(KIT ${PROJECT_NAME})

set(${KIT}_EXPORT_DIRECTIVE "Q_SLICER_MODULE_${MODULE_NAME_UPPER}_WIDGETS_EXPORT")

set(${KIT}_INCLUDE_DIRECTORIES
  ${ModuleDescriptionParser_INCLUDE_DIRS}
  ${MRMLCLI_INCLUDE_DIRS}
  )

set(${KIT}_SRCS
  qSlicerPipelineCLIModulesBridgeParameter.cxx
  qSlicerPipelineCLIModulesBridgeParameter.h
  qSlicerPipelineCLIModulesBridgeParameterFactory.cxx
  qSlicerPipelineCLIModulesBridgeParameterFactory.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesIntegerBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesIntegerBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesFloatBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesFloatBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesDoubleBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesDoubleBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesBooleanBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesBooleanBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesStringBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesStringBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesIntegerVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesIntegerVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesFloatVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesFloatVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesDoubleVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesDoubleVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesStringVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesStringVectorBridgeParameter.h
  )

set(${KIT}_MOC_SRCS
  qSlicerPipelineCLIModulesBridgeParameter.h
  qSlicerPipelineCLIModulesBridgeParameterFactory.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesIntegerBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesFloatBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesDoubleBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesBooleanBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesStringBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesIntegerVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesFloatVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesDoubleVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerPipelineCLIModulesStringVectorBridgeParameter.h
  )

set(${KIT}_UI_SRCS
  )

set(${KIT}_RESOURCES
  )

set(${KIT}_TARGET_LIBRARIES
  ModuleDescriptionParser
  )

#-----------------------------------------------------------------------------
# these files don't actually contain Widgets, but SlicerMacroBuildModuleWidgets
# gets the job done
SlicerMacroBuildModuleWidgets(
  NAME ${KIT}
  EXPORT_DIRECTIVE ${${KIT}_EXPORT_DIRECTIVE}
  INCLUDE_DIRECTORIES ${${KIT}_INCLUDE_DIRECTORIES}
  SRCS ${${KIT}_SRCS}
  MOC_SRCS ${${KIT}_MOC_SRCS}
  UI_SRCS ${${KIT}_UI_SRCS}
  TARGET_LIBRARIES ${${KIT}_TARGET_LIBRARIES}
  RESOURCES ${${KIT}_RESOURCES}
  WRAP_PYTHONQT
  )
