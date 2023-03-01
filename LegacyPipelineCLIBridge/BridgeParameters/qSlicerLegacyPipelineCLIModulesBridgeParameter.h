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

#ifndef __qSlicerLegacyPipelineCLIModulesBridgeParameter_h
#define __qSlicerLegacyPipelineCLIModulesBridgeParameter_h

// Qt includes
#include <QDebug>
#include <QSharedPointer>
#include <QString>
#include <QWidget>

// Bridge Widgets includes
#include "qSlicerLegacyPipelineCLIBridgeModuleWidgetsExport.h"
#include "qSlicerCLIModuleWidget.h"
#include "qSlicerCLIModuleUIHelper.h"

#include <sstream>

//----------------------------------------------------------------------------
// base to specialize from
template <typename T>
struct Converter {
  static T convert(const std::string& s);
  static T convert(const QVariant& v);
};


//----------------------------------------------------------------------------
template <>
struct Converter<int> {
  static int convert(const std::string& s) { return std::stoi(s); }
  static int convert(const QVariant& v) { return v.toInt(); }
};

//----------------------------------------------------------------------------
template <>
struct Converter<double> {
  static double convert(const std::string& s) { return std::stod(s); }
  static double convert(const QVariant& v) { return v.toDouble(); }
};

//----------------------------------------------------------------------------
template <>
struct Converter<float> {
  static float convert(const std::string& s) { return std::stof(s); }
  static float convert(const QVariant& v) { return v.toFloat(); }
};

//----------------------------------------------------------------------------
template <>
struct Converter<bool> {
  static bool convert(const std::string& s) { return s == "true" || s == "True" || s == "1"; }
  static bool convert(const QVariant& v) { return v.toBool(); }
};

//----------------------------------------------------------------------------
template <>
struct Converter<std::string> {
  static std::string convert(const std::string& s) { return s; }
  static std::string convert(const QVariant& v) { return v.toString().toStdString(); }
};

//----------------------------------------------------------------------------
template <>
struct Converter<QString> {
  static QString convert(const std::string& s) { return QString::fromStdString(s); }
  static QString convert(const QVariant& v) { return v.toString(); }
};

//----------------------------------------------------------------------------
template <class T>
struct Converter<std::vector<T>> {
  static std::vector<T> convert(const std::string& s) {
    std::vector<T> result;
    std::stringstream ss(s);
    std::string substr;
    while (ss.good()) {
      getline(ss, substr, ',');
      result.push_back(Converter<T>::convert(substr));
    }
    return result;
  }
  static std::vector<T> convert(const QVariant& v) {
    // vectors are treated as strings by the UI
    return Converter<std::vector<T>>::convert(v.toString().toStdString());
  }
};

//----------------------------------------------------------------------------
template <class T>
struct Converter<QVector<T>> {
  static QVector<T> convert(const std::string& s) {
    QVector<T> result;
    std::stringstream ss(s);
    std::string substr;
    while (ss.good()) {
      getline(ss, substr, ',');
      result.push_back(Converter<T>::convert(substr));
    }
    return result;
  }
  static QVector<T> convert(const QVariant& v) {
    // vectors are treated as strings by the UI
    return Converter<QVector<T>>::convert(v.toString().toStdString());
  }
};

//----------------------------------------------------------------------------
class Q_SLICER_MODULE_LEGACYPIPELINECLIBRIDGE_WIDGETS_EXPORT qSlicerLegacyPipelineCLIModulesBridgeParameter
  : public QObject
{
  Q_OBJECT
public:
  typedef QObject Superclass;
  qSlicerLegacyPipelineCLIModulesBridgeParameter(QObject *parent = nullptr);
  virtual ~qSlicerLegacyPipelineCLIModulesBridgeParameter();

  Q_INVOKABLE void deleteThis();
private:
  Q_DISABLE_COPY(qSlicerLegacyPipelineCLIModulesBridgeParameter);
};

#endif
