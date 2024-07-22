======
SCHISM
======

Grids
------

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.grid.SCHISMGrid

Data
-----

Supporting objects for SCHISM data files.jects

.. autosummary::
   :nosignatures:
   :toctree: _generated/
   rompy.schism.data.SfluxSource
   rompy.schism.data.SfluxAir
   rompy.schism.data.SfluxRad
   rompy.schism.data.SfluxPrc
   rompy.schism.data.SCHISMDataBoundary

Main objects

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.data.SCHISMDataSflux
   rompy.schism.data.SCHISMDataWave
   rompy.schism.data.SCHISMDataOcean
   rompy.schism.data.SCHISMDataTides
   rompy.schism.data.SCHISMData




Config Minimal
---------------

This object has been implemented to meet the initial operational requirements of CSIRO. It is likely that this will be superceded by the full implementation. 

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.config.SchismCSIROConfig

Full Namelist Implementation
-----------------------------

This object implements a set of models for each namelist and assembles a config object using this group of models.  This is curently only partly implemented.  

PARAM
~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.param.PARAM

ICE
~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.ice.ICE

MICE
~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.mice.MICE

ICM
~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.icm.ICM

SEDIMENT
~~~~~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.sediment.SEDIMENT


COSINE
~~~~~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.cosine.COSINE

WWMINPUT_spectra
~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.wwminput_spectra.WWMINPUT

WWMINPUT_ww3
~~~~~~~~~~~~

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.wwminput_WW3.WWMINPUT


NML
~~~~~

This is the full namelist object that is the container for all the other namelist objects.

.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.namelists.NML






Config Object
~~~~~~~~~~~~~~


.. autosummary::
   :nosignatures:
   :toctree: _generated/

   rompy.schism.config.SCHISMConfig
