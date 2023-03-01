project(qSlicer${MODULE_NAME}ModuleWidgets)

find_package(SlicerExecutionModel REQUIRED ModuleDescriptionParser)

macro(ConfigureBridge name underlying_type tag)
  set(BRIDGE_TEMPLATE_NAME ${name})
  set(BRIDGE_TEMPLATE_TYPE ${underlying_type})
  set(BRIDGE_TEMPLATE_TAG ${tag})
  configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/qSlicerLegacyPipelineCLIModulesConcreteBridgeParameter.h.template
    ${CMAKE_CURRENT_BINARY_DIR}/${name}.h
    @ONLY
  )
  configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/qSlicerLegacyPipelineCLIModulesConcreteBridgeParameter.cxx.template
    ${CMAKE_CURRENT_BINARY_DIR}/${name}.cxx
    @ONLY
  )
endmacro()

ConfigureBridge(qSlicerLegacyPipelineCLIModulesIntegerBridgeParameter int integer)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesFloatBridgeParameter float float)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesDoubleBridgeParameter double double)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesBooleanBridgeParameter bool boolean)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesStringBridgeParameter QString string)

ConfigureBridge(qSlicerLegacyPipelineCLIModulesIntegerVectorBridgeParameter std::vector<int> integer-vector)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesFloatVectorBridgeParameter std::vector<float> float-vector)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesDoubleVectorBridgeParameter std::vector<double> double-vector)
#having issues with using std::vector<QString> or QVector<QString> as a return from C++ to Python.
#will be returned as a comma separated string
ConfigureBridge(qSlicerLegacyPipelineCLIModulesStringVectorBridgeParameter QString string-vector)

ConfigureBridge(qSlicerLegacyPipelineCLIModulesIntegerEnumerationBridgeParameter int integer-enumeration)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesFloatEnumerationBridgeParameter float float-enumeration)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesDoubleEnumerationBridgeParameter double double-enumeration)
ConfigureBridge(qSlicerLegacyPipelineCLIModulesStringEnumerationBridgeParameter QString string-enumeration)

set(KIT ${PROJECT_NAME})

set(${KIT}_EXPORT_DIRECTIVE "Q_SLICER_MODULE_${MODULE_NAME_UPPER}_WIDGETS_EXPORT")

set(${KIT}_INCLUDE_DIRECTORIES
  ${ModuleDescriptionParser_INCLUDE_DIRS}
  ${MRMLCLI_INCLUDE_DIRS}
  )

set(${KIT}_SRCS
  qSlicerLegacyPipelineCLIModulesBridgeParameter.cxx
  qSlicerLegacyPipelineCLIModulesBridgeParameter.h
  qSlicerLegacyPipelineCLIModulesBridgeParameterFactory.cxx
  qSlicerLegacyPipelineCLIModulesBridgeParameterFactory.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesBooleanBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesBooleanBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringBridgeParameter.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringVectorBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringVectorBridgeParameter.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerEnumerationBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerEnumerationBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatEnumerationBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatEnumerationBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleEnumerationBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleEnumerationBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringEnumerationBridgeParameter.cxx
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringEnumerationBridgeParameter.h
  )

set(${KIT}_MOC_SRCS
  qSlicerLegacyPipelineCLIModulesBridgeParameter.h
  qSlicerLegacyPipelineCLIModulesBridgeParameterFactory.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesBooleanBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringBridgeParameter.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleVectorBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringVectorBridgeParameter.h

  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesIntegerEnumerationBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesFloatEnumerationBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesDoubleEnumerationBridgeParameter.h
  ${CMAKE_CURRENT_BINARY_DIR}/qSlicerLegacyPipelineCLIModulesStringEnumerationBridgeParameter.h
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
