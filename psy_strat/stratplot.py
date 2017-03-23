"""Module to create new stratographic plots

This module defines the :func:`stratplot` function that can be used to create
stratographic plots such as pollen diagrams
"""
from __future__ import division
import weakref
import six
import matplotlib as mpl
import matplotlib.transforms as mt
from collections import defaultdict
from psyplot.utils import DefaultOrderedDict
import xarray as xr
import numpy as np
from psy_strat.plotters import StratPlotter
import psyplot.project as psy


def stratplot(df, grouper, formatoptions=None, ax=None,
              thresh=0.01, percentages=[], exclude=[],
              widths=None, calculate_percentages=True,
              min_perc=5.0, trunc_height=0.3, fig=None, all_in_one=[]):
    import psyplot.project as psy
    import matplotlib.pyplot as plt
    groups = DefaultOrderedDict(list)
    cols = {}
    for col in df.columns:
        group = grouper(col)
        groups[group].append(col)
        cols[col] = group
    widths = widths or defaultdict(
        lambda: 1. / len(set(groups).difference(percentages)))
    formatoptions = formatoptions or {}

    if calculate_percentages and set(percentages).intersection(groups):
        df = df.copy(True)
        for group in set(percentages).intersection(groups):
            dfp = df.drop([col for col in df.columns
                           if col not in groups[group]], 1)
            for i, row in dfp.iterrows():
                dfp.ix[i, :] = np.asarray(row) / np.sum(row) * 100.
    # NOTE: we create the Dataset manually instead of using
    # xarray.Dataset.from_dataframe becuase that is much faster
    idx = df.index.name
    ds = xr.Dataset(
        {col: xr.Variable((idx), df[col]) for col in df.columns},
        {idx: xr.Variable((idx, ), df.index)})

    for var, varo in ds.variables.items():
        if var not in ds.coords:
            varo.attrs['group'] = cols[var]
    plot_vars = [
        var for var, varo in ds.variables.items()
        if ((var not in ds.coords) and
            (var not in exclude and varo.attrs['group'] not in exclude) and
            (cols[var] not in percentages or ds[var].max().values > thresh))]
    arr_names = []

    if ax is None:
        fig = fig or plt.figure()
        bbox = mt.Bbox.from_extents(
            mpl.rcParams['figure.subplot.left'],
            mpl.rcParams['figure.subplot.bottom'],
            mpl.rcParams['figure.subplot.right'],
            mpl.rcParams['figure.subplot.top'])
    elif isinstance(ax, (mpl.axes.SubplotBase, mpl.axes.Axes)):
        bbox = ax.get_position()
        fig = ax.figure
    else:  # the bbox is given
        bbox = ax
        fig = fig or plt.gcf()
    x0 = bbox.x0
    y0 = bbox.y0
    height = bbox.height - bbox.height * trunc_height
    total_width = bbox.width
    x1 = x0 + total_width

    i = 0
    ax0 = None
    x = x0
    mp = psy.gcp(True)
    with psy.Project.block_signals:
        for group, variables in groups.items():

            variables = [v for v in variables if v in plot_vars]
            if not variables:
                continue
            w = widths[group] * total_width
            if group in all_in_one:
                grouper_cls = StratAllInOne
            elif group in percentages:
                grouper_cls = StratPercentages
            else:
                grouper_cls = StratGroup
            stratgroup = grouper_cls.from_dataset(
                fig, mt.Bbox.from_bounds(x, y0, w, height),
                ds, variables, fmt=dict(formatoptions.get(group, {})),
                project=mp, ax0=ax0)
            stratgroup.group_plots(height)
            ax0 = ax0 or stratgroup.axes[0]
            x += w

            arr_names.extend(arr.psy.arr_name for arr in stratgroup.arrays)

    sp = psy.gcp(True)(arr_name=arr_names)
    for ax, p in sp.axes.items():
        ax_bbox = ax.get_position()
        d = {}
        if ax_bbox.x0 != x0:
            d['left'] = ':'
        if ax_bbox.x1 != x1:
            d['right'] = ':'
        p.update(axislinestyle=d, draw=False)
    psy.scp(sp.main)
    psy.scp(sp)
    return sp


class StratGroup(object):
    """Abstract base class for visualizing stratographic plots"""

    #: list of weakref. Weak references to the created arrays
    _refs = []

    _arrays = None

    #: The default formatoptions for the plots
    default_fmt = {
        'yticks_visible': False,
        }

    @property
    def arrays(self):
        """The arrays managed by this :class:`StratGroup`"""
        return self._arrays or [ref() for ref in self._refs]

    @arrays.setter
    def arrays(self, value):
        self._arrays = value

    @property
    def plotters(self):
        """The plotters of the :attr:`arrays`"""
        return list(filter(lambda p: p is not None,
                           [arr.psy.plotter for arr in self.arrays]))

    @property
    def axes(self):
        return [plotter.ax for plotter in self.plotters]

    @property
    def arr_names(self):
        return [arr.psy.arr_name for arr in self.arrays]

    def __init__(self, arrays, bbox, use_weakref=True):
        """
        Parameters
        ----------
        arrays: list of xarray.DataArray
            The data arrays that are plotted by this :class:`StratGroup`
            instance
        bbox: matplotlib.transforms.Bbox
            The bounding box for the axes
        use_weakref: bool
            If True, only weak references are used
        """
        if use_weakref:
            self._refs = [weakref.ref(arr) for arr in arrays]
        else:
            self.arrays = arrays
        self.bbox = bbox

    def resize_axes(self, axes):
        """Resize the axes in this group"""
        width = self.bbox.width
        w = width / len(axes)
        x0 = self.bbox.x0
        for ax in axes:
            ax_bbox = ax.get_position()
            ax.set_position([x0, ax_bbox.y0, w, ax_bbox.height])
            x0 += w

    def group_plots(self, height):
        self.plotters[0].update(grouper=(height, '%(group)s'),
                                draw=False)

    @classmethod
    def from_dataset(cls, fig, bbox, ds, variables, fmt=None, project=None,
                     ax0=None):
        """
        Create :class:`StratGroup` while creating a stratographic plot

        Create a stratographic plot within the given `bbox` of `fig`.

        Parameters
        ----------
        fig: matplotlib.figure.Figure
            The figure to plot in
        bbox: matplotlib.transforms.Bbox
            The bounding box for the newly created axes
        ds: xarray.Dataset
            The dataset
        variables: list
            The variables that shall be plot in the given `ds`
        project: psyplot.project.Project
            The mother project. If given, only weak references are stored in
            the returned :class:`StratGroup` and each array is appended to the
            `project`.
        ax0: matplotlib.axes.Axes
            The first subplot to share the y-axis with

        Returns
        -------
        StratGroup
            The newly created instance with the arrays
        """
        fmt = fmt or {}
        for key, val in six.iteritems(cls.default_fmt):
            fmt.setdefault(key, val)
        if ax0 is None:
            ax0 = fig.add_axes(bbox.from_bounds(*bbox.bounds), label='ax0')
            axes = [ax0] + [fig.add_axes(bbox.from_bounds(*bbox.bounds),
                                         sharey=ax0, label='ax%i' % i)
                            for i in range(1, len(variables))]
        else:
            axes = [fig.add_axes(bbox.from_bounds(*bbox.bounds),
                                 sharey=ax0, label='ax%i' % i)
                    for i in range(len(variables))]
        sp = psy.Project()._add_data(
            StratPlotter, ds, name=variables, draw=False, fmt=fmt,
            prefer_list=False, ax=axes, share='grouper')
        if project is not None:
            project.extend(sp, new_name=True)
        ret = cls(list(sp), bbox, use_weakref=project is not None)
        ret.resize_axes(axes)
        return ret


class StratPercentages(StratGroup):
    """A :class:`StratGroup` for percentages plots"""

    default_fmt = StratGroup.default_fmt.copy()
    default_fmt['plot'] = 'areax'
    default_fmt['xlim'] = (0, 'rounded')

    def resize_axes(self, axes):
        """Resize the axes in this group"""
        width = self.bbox.width
        width /= sum(ax.get_xlim()[1] for ax in axes) / 100.
        x0 = self.bbox.x0
        for ax in axes:
            w = width * ax.get_xlim()[1] / 100.
            ax_bbox = ax.get_position()
            ax.set_position([x0, ax_bbox.y0, w, ax_bbox.height])
            x0 += w


class StratAllInOne(StratGroup):
    """A :class:`StratGroup` for single plots"""

    default_fmt = StratGroup.default_fmt.copy()
    default_fmt['title'] = '%(group)s'
    default_fmt['titleprops'] = {}
    default_fmt['legend'] = True

    def group_plots(self, height):
        pass

    @classmethod
    def from_dataset(cls, fig, bbox, ds, variables, fmt=None, project=None,
                     ax0=None):
        """
        Create :class:`StratGroup` while creating a stratographic plot

        Create a stratographic plot within the given `bbox` of `fig`.

        Parameters
        ----------
        fig: matplotlib.figure.Figure
            The figure to plot in
        bbox: matplotlib.transforms.Bbox
            The bounding box for the newly created axes
        ds: xarray.Dataset
            The dataset
        variables: list
            The variables that shall be plot in the given `ds`
        project: psyplot.project.Project
            The mother project. If given, only weak references are stored in
            the returned :class:`StratGroup` and each array is appended to the
            `project`.
        ax0: matplotlib.axes.Axes
            The first subplot to share the y-axis with

        Returns
        -------
        StratGroup
            The newly created instance with the arrays
        """
        fmt = fmt or {}
        for key, val in six.iteritems(cls.default_fmt):
            fmt.setdefault(key, val)
        if ax0 is None:
            ax = fig.add_axes(bbox.from_bounds(*bbox.bounds), label='ax0')
        else:
            ax = fig.add_axes(bbox.from_bounds(*bbox.bounds),
                              sharey=ax0, label='ax0')
        sp = psy.Project()._add_data(
            StratPlotter, ds, name=variables, draw=False, fmt=fmt,
            prefer_list=True, ax=ax, share='grouper')
        if project is not None:
            project.extend(sp, new_name=True)
        return cls(list(sp), bbox, use_weakref=project is not None)
