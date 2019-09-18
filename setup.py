"""Setup file for plugin psy-strat

This file is used to install the package to your python distribution.
Installation goes simply via::

    python setup.py install
"""

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys


def readme():
    with open('README.rst') as f:
        return f.read()


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


setup(name='psy-strat',
      version='0.1.1',
      description='A psyplot plugin for stratigraphic plots',
      long_description=readme(),
      classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent',
      ],
      keywords='visualization psyplot pollen',
      url='https://github.com/Chilipp/psy-strat',
      author='Philipp Sommer',
      author_email='philipp.sommer@unil.ch',
      license="GPLv2",
      packages=find_packages(exclude=['docs', 'tests*', 'examples']),
      install_requires=[
          'psyplot>=1.2.0',
          'psy-simple>=1.2.0',
          'xarray!=0.13.0',
      ],
      tests_require=['pytest'],
      cmdclass={'test': PyTest},
      entry_points={
          'psyplot': ['plugin=psy_strat.plugin'],
          'psyplot_gui': [
              'stratplots=psy_strat.strat_widget:StratPlotsWidget'],
          },
      zip_safe=False)
