/*==============================================================================

  Program: 3D Slicer

  Portions (c) Copyright Brigham and Women's Hospital (BWH) All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

==============================================================================*/

// LegacyPipelineCLIBridge includes
#include "qSlicerLegacyPipelineCLIBridgeModule.h"

//-----------------------------------------------------------------------------
/// \ingroup Slicer_QtModules_ExtensionTemplate
class qSlicerLegacyPipelineCLIBridgeModulePrivate
{
public:
  qSlicerLegacyPipelineCLIBridgeModulePrivate();
};

//-----------------------------------------------------------------------------
// qSlicerLegacyPipelineCLIBridgeModulePrivate methods

//-----------------------------------------------------------------------------
qSlicerLegacyPipelineCLIBridgeModulePrivate::qSlicerLegacyPipelineCLIBridgeModulePrivate()
{
}

//-----------------------------------------------------------------------------
// qSlicerLegacyPipelineCLIBridgeModule methods

//-----------------------------------------------------------------------------
qSlicerLegacyPipelineCLIBridgeModule::qSlicerLegacyPipelineCLIBridgeModule(QObject* _parent)
  : Superclass(_parent)
  , d_ptr(new qSlicerLegacyPipelineCLIBridgeModulePrivate)
{
}

//-----------------------------------------------------------------------------
qSlicerLegacyPipelineCLIBridgeModule::~qSlicerLegacyPipelineCLIBridgeModule()
{
}

//-----------------------------------------------------------------------------
QString qSlicerLegacyPipelineCLIBridgeModule::helpText() const
{
  return "The files in this directory exist to bridge the gap between the `qSlicerCLIModuleUIHelper`,"
         " written in C++ and the Python code of the pipeline creator."
         " The bridge parameters are classes derived from QObject that meet the interface expected by"
         " the pipeline creator for pipeline parameters (two functions: `GetValue() -> SomeValueType`"
         " and `GetUI() -> QWidget or QLayout`). They are C++ classes wrapped by the Qt Python wrapping"
         " mechanism in CMake. The bridge factory creates the appropriate bridge parameter type for a CLI parameter.";
}

//-----------------------------------------------------------------------------
QString qSlicerLegacyPipelineCLIBridgeModule::acknowledgementText() const
{
  return "This module was originally developed by Connor Bowley (Kitware, Inc.) for SlicerSALT.";
}

//-----------------------------------------------------------------------------
QStringList qSlicerLegacyPipelineCLIBridgeModule::contributors() const
{
  QStringList moduleContributors;
  moduleContributors << QString("Connor Bowley (Kitware, Inc.)");
  return moduleContributors;
}

//-----------------------------------------------------------------------------
QIcon qSlicerLegacyPipelineCLIBridgeModule::icon() const
{
  return QIcon(":/Icons/LegacyPipelineCLIBridge.png");
}

//-----------------------------------------------------------------------------
QStringList qSlicerLegacyPipelineCLIBridgeModule::categories() const
{
  return QStringList() << "Pipelines.Advanced";
}

//-----------------------------------------------------------------------------
QStringList qSlicerLegacyPipelineCLIBridgeModule::dependencies() const
{
  return QStringList();
}

//-----------------------------------------------------------------------------
void qSlicerLegacyPipelineCLIBridgeModule::setup()
{
  this->Superclass::setup();
}

//-----------------------------------------------------------------------------
qSlicerAbstractModuleRepresentation* qSlicerLegacyPipelineCLIBridgeModule
::createWidgetRepresentation()
{
  return nullptr;
}

//-----------------------------------------------------------------------------
vtkMRMLAbstractLogic* qSlicerLegacyPipelineCLIBridgeModule::createLogic()
{
  return nullptr;
}

//-----------------------------------------------------------------------------
bool qSlicerLegacyPipelineCLIBridgeModule::isHidden() const
{
  return true;
}
