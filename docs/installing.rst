.. _install:

.. highlight:: bash

Installation
============

How to install
--------------

Installation using conda
^^^^^^^^^^^^^^^^^^^^^^^^
We highly recommend to use conda_ for installing psy-strat. After downloading
the installer from anaconda_, you can install psy-strat simply via::

    $ conda install -c chilipp psy-strat

.. _anaconda: https://www.continuum.io/downloads
.. _conda: http://conda.io/

Installation using pip
^^^^^^^^^^^^^^^^^^^^^^
If you do not want to use conda for managing your python packages, you can also
use the python package manager ``pip`` and install via::

    $ pip install psy-strat

Running the tests
-----------------
First, clone out the github_ repository. Then run::

    $ python setup.py test

or after having install pytest_::

    $ py.test


.. _pytest: https://pytest.org/latest/contents.html
.. _github: https://github.com/Chilipp/psy-strat
