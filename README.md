SlicerPipelines
---------------

SlicerPipelines is an extension for 3D Slicer for creating and executing simple modules (aka pipelines) via a GUI interface with no coding knowledge needed.


## Overview

The SlicerPipelines extension allows to create and execute simple linear workflows using the `PipelineCreator` and the `PipelineCaseIterator` modules.

The design and implementation of this extension was initially motivated to simplify the creation of shape analysis workflow specific to the SlicerSALT community.

## Features

* **Simple**: Create and execute pipelines with a few clicks.
* **Composable**: Pipelines are themselve modules available as "steps" to create new pipelines.
* **Extensible**: Regular Slicer module modules, python functions, or executable can be registered as pipeline steps.


## Screenshots

![PipelineCreator module](Screenshots/1.png)
![Select Module pop up](Screenshots/2.png)

## Resources

To learn more about Slicer, SlicerSALT, and Slicer extensions, check out the following resources.

 - https://slicer.readthedocs.io/en/latest/
 - https://salt.slicer.org/
 - https://slicer.readthedocs.io/en/latest/user_guide/extensions_manager.html

## License

This software is licensed under the terms of the [Apache Licence Version 2.0](LICENSE).

