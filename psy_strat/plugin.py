"""psy-strat psyplot plugin

This module defines the rcParams for the psy-strat plugin. This module will
be imported when psyplot is imported. What is should contain is:

- an rcParams variable as instance of :class:`psyplot.config.rcsetup.RcParams`
  that describes the configuration of your plugin
- a get_versions function that returns the version of your plugin and the ones
  from its requirements

.. warning::

    Because of recursion issues, You have to load the psyplot module before
    loading this module! In other words, you have to type

    .. code-block:: python

        import psyplot
        import psy_strat.plugin"""
from psyplot.config.rcsetup import RcParams
from psy_strat import __version__ as plugin_version
from itertools import repeat
from psy_simple.plugin import (
    rcParams as psys_rcParams, validate_bool, validate_int, try_and_error,
    validate_none, validate_float, validate_str, validate_color,
    validate_lineplot, validate_marker, ValidateList, ValidateInStrings)


def get_versions(requirements=True):
    """Get the versions of psy-strat and it's requirements

    Parameters
    ----------
    requirements: bool
        If True, the requirements are imported and it's versions are included
    """
    ret = {'version': plugin_version}
    if requirements:
        # insert versions of the requirements, e.g. via
        #   >>> import requirement
        #   >>> ret['requirement'] = requirement.__version__
        pass
    return ret


# -----------------------------------------------------------------------------
# ------------------------- validation functions ------------------------------
# -----------------------------------------------------------------------------


# define your validation functions for the values in the rcParams here. If
# a validation fails, the function should raise a ValueError or TypeError


def validate_grouper(value):
    """
    Validate the grouper formatoption

    Parameters
    ----------
    value: tuple (float ``y1``, str ``s``)
        A tuple of length 2, where the first parameter ``0<=y1<=1`` determines
        the distance of the bar to the top y-axis and the second is the title
        of the group
    """
    y1, s = value
    y1 = validate_float(y1)
    s = validate_str(s)
    return y1, s


def validate_axislinestyle(value):
    """Validate a dictionary containing axiscolor definitions

    Parameters
    ----------
    value: dict
        a mapping from 'left', 'right', 'bottom', 'top' to the linestyle

    Returns
    -------
    dict

    Raises
    ------
    ValueError"""
    validate = try_and_error(validate_none, validate_str)
    possible_keys = {'right', 'left', 'top', 'bottom'}
    try:
        value = dict(value)
        false_keys = set(value) - possible_keys
        if false_keys:
            raise ValueError("Wrong keys (%s)!" % (', '.join(false_keys)))
        for key, val in value.items():
            value[key] = validate(val)
    except Exception:
        value = dict(zip(possible_keys, repeat(validate(value))))
    return value


def validate_hlines(value):
    """Validate the hlines formatoption

    Parameters
    ----------
    value: object
        Either None, True or a color"""
    if value is None:
        return value
    elif value is True:
        return '0.9'
    return validate_color(value)


# -----------------------------------------------------------------------------
# ------------------------------ rcParams -------------------------------------
# -----------------------------------------------------------------------------


# define your defaultParams. A mapping from rcParams key to a list of length 3:
#
# 1. the default value
# 2. the validation function of type conversion function
# 3. a short description of the default value
#
# Example::
#
#     defaultParams = {'my.key': [True, bool, 'What my key does']}

psys_validate = psys_rcParams.validate
psys_desc = psys_rcParams.descriptions
defaultParams = {

    # if you define new plotters, we recommend to assign a specific rcParams
    # key for it, e.g.
    'plotter.strat.transpose': [
        True, psys_validate['plotter.simple.transpose'],
        'fmt key to switch x- and y-axis for stratigraphic plots'],
    'plotter.strat.title_loc': [
        'left', ValidateInStrings('title_loc', ['center', 'left', 'right'],
                                  True)],
    'plotter.strat.titleprops': [
        {'rotation': 45, 'va': 'bottom', 'ha': 'left',
         'bbox': {'facecolor': 'w', 'edgecolor': 'none'}},
        psys_validate['plotter.baseplotter.titleprops'],
        'The properties of the axes title'],
    'plotter.strat.legendlabels': [
        '%(name)s', psys_validate['plotter.simple.legendlabels'],
        psys_desc['plotter.simple.legendlabels']],
    'plotter.strat.legend': [
        False, psys_validate['plotter.simple.legend'],
        psys_desc['plotter.simple.legend']],
    'plotter.strat.titlesize': [
        'small',
        psys_validate['plotter.baseplotter.titlesize'],
        psys_desc['plotter.baseplotter.titlesize']],
    'plotter.strat.title': [
        '%(name)s',
        psys_validate['plotter.baseplotter.title'],
        'The axes title'],
    'plotter.strat.title_wrap': [
        15, validate_int, 'wrap the title after the given amount of characters'
        ],
    'plotter.strat.hlines': [
        None, try_and_error(validate_none, validate_grouper),
        'Show the measurements'],
    'plotter.strat.grouper': [
        None, try_and_error(validate_none, validate_grouper),
        'Group several plots together using the grouper formatoption'],
    'plotter.strat.grouperweight': [
        psys_rcParams['plotter.baseplotter.titleweight'],
        psys_validate['plotter.baseplotter.titleweight'],
        'Set the fontweight of the grouper text'],
    'plotter.strat.groupersize': [
        psys_rcParams['plotter.baseplotter.titlesize'],
        psys_validate['plotter.baseplotter.titlesize'],
        'Set the fontsize of the grouper text'],
    'plotter.strat.grouperprops': [
        {'bbox': {'facecolor': 'w', 'edgecolor': 'none'}},
        psys_validate['plotter.baseplotter.titleprops'],
        'Set the font properties of the grouper text'],
    'plotter.strat.axislinestyle': [
        None, validate_axislinestyle,
        'The linestyle of the x- and y-axes'],
    'plotter.strat.exag_color': [
        '0.7', psys_validate['plotter.simple.color'],
        'The color for exaggerations'],
    'plotter.strat.exag_factor': [
        10, validate_float, 'The exaggeration factor'],
    'plotter.strat.exag': [
        None, validate_lineplot, 'The plotting style for exaggerations'],
    'plotter.strat.occurences': [
        None, try_and_error(validate_none, validate_float,
                            ValidateList(float, 2)),
        "The range that should be considered as an occurence"],
    'plotter.strat.occurence_marker': [
        '+', validate_marker, 'The symbol of the marker for occurences'],
    'plotter.strat.occurence_value': [
        None, try_and_error(validate_none, validate_float,
                            ValidateList(float)),
        'The value to use for an occurence in the plot']
    }

# create the rcParams and populate them with the defaultParams. For more
# information on this class, see the :class:`psyplot.config.rcsetup.RcParams`
# class
rcParams = RcParams(defaultParams=defaultParams)
rcParams.update_from_defaultParams()
