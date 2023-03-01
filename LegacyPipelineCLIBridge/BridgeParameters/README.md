# Bridge Parameters

The files in this directory exist to bridge the gap between the `qSlicerCLIModuleUIHelper`,
written in C++ and the Python code of the pipeline creator.

The bridge parameters are classes derived from QObject that meet the interface expected by the pipeline creator for pipeline parameters (two functions: `GetValue() -> SomeValueType` and `GetUI() -> QWidget or QLayout`). They are C++ classes wrapped by the Qt Python wrapping mechanism in CMake. The bridge factory creates the appropriate bridge parameter type for a CLI parameter.

##  Why wasn't at least the factory part done in a module logic?

At the time of this implementation, there are 2 ways of Python wrapping C++ code that get done automagically as part of the CMake infrastructure, a Qt wrapping and a VTK wrapping. The VTK wrapping portion wraps all VTK classes, including slicer logics. Any function of a VTK class that has a type in its signature that the wrapping doesn't understand gets ignored. A critical type that is needed by the pipeline creator that VTK wrapping doesn't understand is `QWidget*`. This prevents us from using VTK based classes as pipeline parameters (which need `GetUI()` function that returns a `QWidget`). The slicer logic classes are VTK based and can only return `vtkObjects` or built in types like primatives and some `std` containers. Because we can't use VTK based classes as pipeline parameters, we can't use a slicer logic to return pipeline parameters.

## Why doesn't the qSlicerLegacyPipelineCLIModulesBridgeParameter base class offer any kind of interface to use it? Why have it at all?

The bridge parameters and bridge factory are in an interesting spot. They are C++ code that is solely intended to be used by Python code. C++ requires that function signatures cannot vary only in return type, hence returning a base class. Multiple functions "`CreateIntegerParameterWrapper/CreateFloatParameterWrapper/etc`" were not desired since the whole point of the factory was to decide on and create the correct the parameter type. But the interaction between the C++ type system and the Python type system is interesting. Python doesn't have the concept of "downcasting". You always have access to the most derived type's interface. So when I return a base class in C++, I actually "get" the derived class in Python. So I end up with one C++ function capable of returning different types to Python code, no casting required.

## Why does the factory keep ownership of the parameters?

When I returned a raw owning pointer, the generated Python wrapping never deleted it. When I returned a `QSharedPointer` I got errors at runtime saying Python didn't know what a `QSharedPointer<qSlicerLegacyPipelineCLIModulesBridgeParameter>` was. Because the factory owns and deletes the bridge parameters, the bridge parameters cannot outlive the factory. Ensuring this is the purpose of the Python class `CLIModuleWrapping.BridgeParameterWrapper` and the reason behind the "yet another" wrapper class.

## Other notes:

Originally I wanted the factory's `CreateParameterWrapper` method to take `vtkMRMLCommandLineModuleNode*` directly as a parameter and skip the whole `loadCLIModule` step. I found that the way that the Qt Python wrapping interacts with the VTK Python wrapping didn't allow that. When I passed a VTK Wrapped `vtkMRMLCommandLineModuleNode` to a Qt wrapped function that took a `vtkMRMLCommandLineModuleNode*`, it caused the application to crash. This is the reason the parameters became strings for both the `cliModuleName` in `loadCLIModule` and the `parameterName` in `CreateParameterWrapper` (although there wasn't any Python wrapping for `ModuleParameter` anyway).
