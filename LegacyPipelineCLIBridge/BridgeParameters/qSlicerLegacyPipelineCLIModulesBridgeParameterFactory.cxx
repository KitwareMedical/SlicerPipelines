/*==============================================================================

  Program: 3D Slicer

  Copyright (c) Kitware Inc.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
  and was partially funded by NIH grant 3P41RR013218-12S1

==============================================================================*/

// Bridge Widgets includes
#include "qSlicerLegacyPipelineCLIModulesBridgeParameterFactory.h"

#include "qSlicerLegacyPipelineCLIModulesIntegerBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesFloatBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesDoubleBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesBooleanBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesStringBridgeParameter.h"

#include "qSlicerLegacyPipelineCLIModulesIntegerVectorBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesFloatVectorBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesDoubleVectorBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesStringVectorBridgeParameter.h"

#include "qSlicerLegacyPipelineCLIModulesIntegerEnumerationBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesFloatEnumerationBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesDoubleEnumerationBridgeParameter.h"
#include "qSlicerLegacyPipelineCLIModulesStringEnumerationBridgeParameter.h"

#include <qSlicerCoreApplication.h>
#include <vtkSlicerCLIModuleLogic.h>
#include <qSlicerCLIModule.h>
#include <qSlicerModuleManager.h>

//-----------------------------------------------------------------------------
class qSlicerLegacyPipelineCLIModulesBridgeParameterFactoryPrivate
{
  Q_DECLARE_PUBLIC(qSlicerLegacyPipelineCLIModulesBridgeParameterFactory);
protected:
  qSlicerLegacyPipelineCLIModulesBridgeParameterFactory* const q_ptr;

public:
  qSlicerLegacyPipelineCLIModulesBridgeParameterFactoryPrivate(
    qSlicerLegacyPipelineCLIModulesBridgeParameterFactory& object);
  virtual void setupUi(qSlicerLegacyPipelineCLIModulesBridgeParameterFactory*);

  vtkMRMLCommandLineModuleNode* CliNode;

  template <class T>
  T* createAndInitialize(const ModuleParameter& moduleParameter) {
    // temporarily store in unique ptr in case Initialize throws (it shouldn't)
    auto p = std::unique_ptr<T>(new T);
    try {
      p->Initialize(moduleParameter);
      return p.release();
    } catch (...) {
      throw;
    }
  }
};

// --------------------------------------------------------------------------
qSlicerLegacyPipelineCLIModulesBridgeParameterFactoryPrivate
::qSlicerLegacyPipelineCLIModulesBridgeParameterFactoryPrivate(
  qSlicerLegacyPipelineCLIModulesBridgeParameterFactory& object)
  : q_ptr(&object)
{
}

// --------------------------------------------------------------------------
void qSlicerLegacyPipelineCLIModulesBridgeParameterFactoryPrivate
::setupUi(qSlicerLegacyPipelineCLIModulesBridgeParameterFactory*)
{}

//-----------------------------------------------------------------------------
// qSlicerLegacyPipelineCLIModulesBridgeParameterFactory methods

//-----------------------------------------------------------------------------
qSlicerLegacyPipelineCLIModulesBridgeParameterFactory
::qSlicerLegacyPipelineCLIModulesBridgeParameterFactory(QWidget* parentWidget)
  : Superclass( parentWidget )
  , d_ptr( new qSlicerLegacyPipelineCLIModulesBridgeParameterFactoryPrivate(*this) )
{
}

//-----------------------------------------------------------------------------
qSlicerLegacyPipelineCLIModulesBridgeParameterFactory
::~qSlicerLegacyPipelineCLIModulesBridgeParameterFactory()
{
  Q_D(qSlicerLegacyPipelineCLIModulesBridgeParameterFactory);
  if (d->CliNode) {
    auto mrmlScene = d->CliNode->GetScene();
    if (mrmlScene) {
      mrmlScene->RemoveNode(d->CliNode);
    }
  }
}

//---------------------------------------------------------------------------
qSlicerLegacyPipelineCLIModulesBridgeParameter* qSlicerLegacyPipelineCLIModulesBridgeParameterFactory::CreateParameterWrapper(const ModuleParameter& moduleParameter)
{
  Q_D(qSlicerLegacyPipelineCLIModulesBridgeParameterFactory);
  const bool multiple = moduleParameter.GetMultiple() == "true";
  if (!multiple && moduleParameter.GetTag() == "integer") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesIntegerBridgeParameter>(moduleParameter);
  } else if (!multiple && moduleParameter.GetTag() == "float") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesFloatBridgeParameter>(moduleParameter);
  }  else if (!multiple && moduleParameter.GetTag() == "double") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesDoubleBridgeParameter>(moduleParameter);
  } else if (!multiple && moduleParameter.GetTag() == "boolean") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesBooleanBridgeParameter>(moduleParameter);
  } else if (!multiple && moduleParameter.GetTag() == "string") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesStringBridgeParameter>(moduleParameter);
  }
  else if ((!multiple && moduleParameter.GetTag() == "integer-vector") || (multiple && moduleParameter.GetTag() == "integer")) {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesIntegerVectorBridgeParameter>(moduleParameter);
  } else if ((!multiple && moduleParameter.GetTag() == "float-vector") || (multiple && moduleParameter.GetTag() == "float")) {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesFloatVectorBridgeParameter>(moduleParameter);
  } else if ((!multiple && moduleParameter.GetTag() == "double-vector") || (multiple && moduleParameter.GetTag() == "double")) {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesDoubleVectorBridgeParameter>(moduleParameter);
  } else if ((!multiple && moduleParameter.GetTag() == "string-vector") || (multiple && moduleParameter.GetTag() == "string")) {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesStringVectorBridgeParameter>(moduleParameter);
  }
  else if (!multiple && moduleParameter.GetTag() == "integer-enumeration") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesIntegerEnumerationBridgeParameter>(moduleParameter);
  } else if (!multiple && moduleParameter.GetTag() == "float-enumeration") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesFloatEnumerationBridgeParameter>(moduleParameter);
  } else if (!multiple && moduleParameter.GetTag() == "double-enumeration") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesDoubleEnumerationBridgeParameter>(moduleParameter);
  } else if (!multiple && moduleParameter.GetTag() == "string-enumeration") {
    return d->createAndInitialize<qSlicerLegacyPipelineCLIModulesStringEnumerationBridgeParameter>(moduleParameter);
  }
  else {
    std::stringstream ss;
    ss << "Unknown parameter: " << moduleParameter.GetName() << " of type "
      << (multiple ? std::string("multiple ") : std::string("")) << moduleParameter.GetTag() << std::endl;
    std::cerr << ss.str() << std::endl;
    throw std::invalid_argument(ss.str());
  }
}

//-----------------------------------------------------------------------------
qSlicerLegacyPipelineCLIModulesBridgeParameter*
qSlicerLegacyPipelineCLIModulesBridgeParameterFactory::CreateParameterWrapper(const QString& parameterName)
{
  Q_D(qSlicerLegacyPipelineCLIModulesBridgeParameterFactory);
  if (!d->CliNode) {
    std::cerr << "Must load a cli module before creating parameter wrappers" << std::endl;
    return nullptr;
  }

  auto& moduleDescription = d->CliNode->GetModuleDescription();

  const auto stdParameterName = parameterName.toStdString();

  const auto& parameterGroups = moduleDescription.GetParameterGroups();
  for (const auto& group : parameterGroups) {
    for (const auto& parameter : group.GetParameters()) {
      if (parameter.GetName() == stdParameterName) {
        return this->CreateParameterWrapper(parameter);
      }
    }
  }

  std::cerr << "Unable to find parameter with name: " << stdParameterName << std::endl;
  return nullptr;
}

//-----------------------------------------------------------------------------
void qSlicerLegacyPipelineCLIModulesBridgeParameterFactory::loadCLIModule(const QString& cliModuleName)
{
  Q_D(qSlicerLegacyPipelineCLIModulesBridgeParameterFactory);

  auto cliModule = dynamic_cast<qSlicerCLIModule*>(qSlicerCoreApplication::application()->moduleManager()->module(cliModuleName));
  if (!cliModule) {
    std::cerr << "Unable to find a qSlicerCLIModule with the name: " << cliModuleName.toStdString() << std::endl;
  }

  vtkSlicerCLIModuleLogic* moduleLogic = vtkSlicerCLIModuleLogic::SafeDownCast(cliModule->logic());
  if (!moduleLogic) {
    std::cerr << "Unable to find a vtkSlicerCLIModuleLogic for module with the name: " << cliModuleName.toStdString() << std::endl;
  }

  // create CLI module node
  vtkMRMLCommandLineModuleNode* cliNode = moduleLogic->CreateNodeInScene();
  if (!cliNode) {
    std::cerr << "Unable to create a vtkMRMLCommandLineModuleNode for module with the name: " << cliModuleName.toStdString() << std::endl;
  }

  d->CliNode = cliNode;
}
