================
Model Components
================

Add quick paragraph describing the idea behind the components and subcomponents.
Describe the minimum requirement of component and subcomponent classes. The role
of `model_type` when using a declarative approach. The render() method and how
it is used to generate the command line specification.

TODO: Ensure the `model_type` is shown next to each class in the autosummaries.

Components
----------

Components render an entire SWAN command line specification.

* :doc:`components/startup`
* :doc:`components/cgrid`
* :doc:`components/inpgrid`
* :doc:`components/boundary`
* :doc:`components/physics`
* :doc:`components/numerics`
* :doc:`components/output`
* :doc:`components/lockup`


Subcomponents
-------------

Subcomponents render part of a SWAN command line specification. They typically define
specific arguments to one or more component.

* :doc:`subcomponents/startup`
* :doc:`subcomponents/spectrum`
* :doc:`subcomponents/cgrid`
* :doc:`subcomponents/time`
* :doc:`subcomponents/readgrid`
* :doc:`subcomponents/boundary`
* :doc:`subcomponents/physics`
