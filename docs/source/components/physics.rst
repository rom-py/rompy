.. currentmodule: rompy

=======
Physics
=======

Components and subcomponents to describe all physics settings in SWAN.

Components
----------

Wave generation
~~~~~~~~~~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: generated/

   rompy.swan.components.physics.GEN1
   rompy.swan.components.physics.GEN2
   rompy.swan.components.physics.GEN3
   rompy.swan.components.physics.GT6

Swell dissipation
~~~~~~~~~~~~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: generated/

   rompy.swan.components.physics.NEGATINP
   rompy.swan.components.physics.ARDHUIN
   rompy.swan.components.physics.ZIEGER
   rompy.swan.components.physics.ROGERS


Subcomponents
-------------

Source terms
~~~~~~~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: generated/

   rompy.swan.subcomponents.physics.JANSSEN
   rompy.swan.subcomponents.physics.KOMEN
   rompy.swan.subcomponents.physics.WESTHUYSEN
   rompy.swan.subcomponents.physics.ST6

**ST6 presets**

Combinations of calibrated coefficients for ST6 are defined in the `SWAN Manual`_.
The following presets are available to easily prescribe one of those combinations.

.. autosummary::
   :nosignatures:
   :toctree: generated/

   rompy.swan.subcomponents.physics.ST6C1
   rompy.swan.subcomponents.physics.ST6C2
   rompy.swan.subcomponents.physics.ST6C3
   rompy.swan.subcomponents.physics.ST6C4
   rompy.swan.subcomponents.physics.ST6C5



.. _`SWAN Manual`: https://swanmodel.sourceforge.io/online_doc/swanuse/node28.html
