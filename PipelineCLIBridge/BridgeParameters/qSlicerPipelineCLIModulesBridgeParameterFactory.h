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

#ifndef __qSlicerPipelineCLIModulesBridgeParameterFactory_h
#define __qSlicerPipelineCLIModulesBridgeParameterFactory_h

// Qt includes
#include <QString>
#include <QWidget>

// Bridge Widgets includes
#include "qSlicerPipelineCLIModulesBridgeParameter.h"
#include "qSlicerPipelineCLIBridgeModuleWidgetsExport.h"
#include "vtkMRMLCommandLineModuleNode.h"

class qSlicerPipelineCLIModulesBridgeParameterFactoryPrivate;
class Q_SLICER_MODULE_PIPELINECLIBRIDGE_WIDGETS_EXPORT qSlicerPipelineCLIModulesBridgeParameterFactory
  : public QWidget
{
  Q_OBJECT
public:
  typedef QWidget Superclass;
  qSlicerPipelineCLIModulesBridgeParameterFactory(QWidget *parent=0);
  virtual ~qSlicerPipelineCLIModulesBridgeParameterFactory();

  /// IMPORTANT: The returned pointer is owned by this object and will be deleted in this object's destructor
  Q_INVOKABLE qSlicerPipelineCLIModulesBridgeParameter* CreateParameterWrapper(const QString& parameterName);
  Q_INVOKABLE void loadCLIModule(const QString& cliModuleName);

protected:
  QScopedPointer<qSlicerPipelineCLIModulesBridgeParameterFactoryPrivate> d_ptr;

private:
  qSlicerPipelineCLIModulesBridgeParameter* CreateParameterWrapper(const ModuleParameter& moduleParameter);
  Q_DECLARE_PRIVATE(qSlicerPipelineCLIModulesBridgeParameterFactory);
  Q_DISABLE_COPY(qSlicerPipelineCLIModulesBridgeParameterFactory);
};

#endif
