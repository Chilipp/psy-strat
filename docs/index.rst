.. psy-strat documentation master file, created by
   sphinx-quickstart on Wed Oct 31 15:03:18 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _psy-strat:

psy-strat: A psyplot plugin for stratigraphic plots
========================================================

Welcome to the psyplot plugin for stratigraphic visualization. This package
defines the :func:`~psy_strat.stratplot.stratplot` function that visualizes
a dataframe in a stratigraphic plot.

Additionally, this plugin interfaces with the
:ref:`psyplot GUI <psyplot_gui:psyplot-gui>` package to allow you an
interactive manipulation of the stratigraphic plot.

See the :ref:`gallery_examples` for more information.

.. start-badges

.. only:: html and not epub

    .. list-table::
        :stub-columns: 1
        :widths: 10 90

        * - docs
          - |docs|
        * - tests
          - |travis| |appveyor| |requires| |coveralls|
        * - package
          - |version| |conda| |supported-versions| |supported-implementations| |zenodo|

    .. |docs| image:: http://readthedocs.org/projects/psy-strat/badge/?version=latest
        :alt: Documentation Status
        :target: http://psy-strat.readthedocs.io/en/latest/?badge=latest

    .. |travis| image:: https://travis-ci.org/Chilipp/psy-strat.svg?branch=master
        :alt: Travis
        :target: https://travis-ci.org/Chilipp/psy-strat

    .. |appveyor| image:: https://ci.appveyor.com/api/projects/status/pv9kyd8obfrqp5wf?svg=true
        :alt: AppVeyor
        :target: https://ci.appveyor.com/project/Chilipp/psy-strat

    .. |coveralls| image:: https://coveralls.io/repos/github/Chilipp/psy-strat/badge.svg?branch=master
        :alt: Coverage
        :target: https://coveralls.io/github/Chilipp/psy-strat?branch=master

    .. |requires| image:: https://requires.io/github/Chilipp/psy-strat/requirements.svg?branch=master
        :alt: Requirements Status
        :target: https://requires.io/github/Chilipp/psy-strat/requirements/?branch=master

    .. |version| image:: https://img.shields.io/pypi/v/psy-strat.svg?style=flat
        :alt: PyPI Package latest release
        :target: https://pypi.python.org/pypi/psy-strat

    .. |conda| image:: https://anaconda.org/conda-forge/psy-strat/badges/version.svg
        :alt: conda
        :target: https://anaconda.org/conda-forge/psy-strat

    .. |supported-versions| image:: https://img.shields.io/pypi/pyversions/psy-strat.svg?style=flat
        :alt: Supported versions
        :target: https://pypi.python.org/pypi/psy-strat

    .. |supported-implementations| image:: https://img.shields.io/pypi/implementation/psy-strat.svg?style=flat
        :alt: Supported implementations
        :target: https://pypi.python.org/pypi/psy-strat

    .. |zenodo| image:: https://zenodo.org/badge/81938204.svg
        :alt: Zenodo
        :target: https://zenodo.org/badge/latestdoi/81938204

.. end-badges


Documentation
-------------

.. toctree::
    :maxdepth: 1

    installing
    examples/index
    api/psy_strat



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
