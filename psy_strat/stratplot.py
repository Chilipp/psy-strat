"""Module to create new stratographic plots

This module defines the :func:`stratplot` function that can be used to create
stratographic plots such as pollen diagrams
"""
from __future__ import division
import weakref
import six
from itertools import groupby
import matplotlib as mpl
import matplotlib.transforms as mt
from collections import defaultdict
import psyplot
from psyplot.utils import DefaultOrderedDict
import xarray as xr
import numpy as np
from psy_strat.plotters import StratPlotter
from psyplot.data import ArrayList
import psyplot.project as psy


gui_plugin = 'psy_strat.strat_widget:StratPlotsWidget:stratplots'


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
    groupers = []
    with psy.Project.block_signals:
        for group, variables in groups.items():

            variables = [v for v in variables if v in plot_vars]
            if not variables:
                continue
            w = widths[group] * total_width
            if group in all_in_one:
                identifier = 'all_in_one'
            elif group in percentages:
                identifier = 'percentages'
            else:
                identifier = 'default'
            grouper_cls = strat_groupers[identifier]
            grouper = grouper_cls.from_dataset(
                fig, mt.Bbox.from_bounds(x, y0, w, height),
                ds, variables, fmt=dict(formatoptions.get(group, {})),
                project=mp, ax0=ax0)
            grouper.group_plots(height)
            ds[group] = xr.Variable(tuple(), '',
                                    attrs={'identifier': identifier})
            ax0 = ax0 or grouper.axes[0]
            x += w

            arr_names.extend(
                arr.psy.arr_name for arr in grouper.plotter_arrays)
            groupers.append(grouper)
        if psyplot.with_gui:
            from psyplot_gui.main import mainwindow
            mainwindow.plugins[gui_plugin].add_tree(groupers)

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

    _plotter_arrays = None

    grouper_height = None

    #: The default formatoptions for the plots
    default_fmt = {
        'yticks_visible': False,
        }

    @property
    def plotter_arrays(self):
        """The data objects that contain the plotters"""
        return self._plotter_arrays or ArrayList([ref() for ref in self._refs])

    @plotter_arrays.setter
    def plotter_arrays(self, value):
        self._plotter_arrays = value

    @property
    def arrays(self):
        """The arrays managed by this :class:`StratGroup`. One array for each
        variable"""
        return self.plotter_arrays

    @property
    def all_arrays(self):
        """All variables of this group in the dataset"""
        arr = self.arrays[0]
        group = arr.group
        ds = arr.psy.base
        return [ds.psy[arr] for arr, v in ds.variables.items()
                if v.attrs.get('group') == group]

    @property
    def plotters(self):
        """The plotters of the :attr:`arrays`"""
        return list(filter(lambda p: p is not None,
                           [arr.psy.plotter for arr in self.plotter_arrays]))

    @property
    def axes(self):
        return [plotter.ax for plotter in self.plotters]

    @property
    def arr_names(self):
        return [arr.psy.arr_name for arr in self.plotter_arrays]

    @property
    def group(self):
        """The name of the group of the arrays in this grouper"""
        return self.arrays[0].group

    def __init__(self, arrays, bbox=None, use_weakref=True):
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
            self.plotter_arrays = arrays
        if bbox is None:
            boxes = [arr.psy.ax.get_position() for arr in arrays]
            x0 = min(bbox.x0 for bbox in boxes)
            y0 = min(bbox.y0 for bbox in boxes)
            w = sum(bbox.width for bbox in boxes)
            bbox = boxes[0].from_bounds(x0, y0, w, boxes[0].height)
        self.bbox = bbox
        group = self.group
        for arr in arrays:
            arr.attrs['group'] = group

    def resize_axes(self, axes):
        """Resize the axes in this group"""
        width = self.bbox.width
        w = width / len(axes)
        x0 = self.bbox.x0
        for ax in axes:
            ax_bbox = ax.get_position()
            ax.set_position([x0, ax_bbox.y0, w, ax_bbox.height])
            x0 += w

    def group_plots(self, height=None):
        plotter = next((plotter for plotter in self.plotters
                        if plotter.ax.get_visible()), None)
        if plotter is None:
            return
        height = height or self.grouper_height
        if height is None:
            height = plotter['grouper'][0]
        self.grouper_height = height
        plotter.update(grouper=(height, '%(group)s'),
                       draw=False, force=True)
        for p in self.plotters:
            with p.no_validation:
                p['grouper'] = (height, '%(group)s')

    @property
    def figure(self):
        """The figure that contains the plots"""
        return self.axes[0].figure

    def is_visible(self, arr):
        """Check if the given `arr` is shown"""
        return arr.psy.plotter.ax.get_visible()

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

    def hide_array(self, name):
        """Hide the variable of the given `name`

        Parameters
        ----------
        name: str
            The variable name"""
        arr = next(iter(self.plotter_arrays(name=name)), None)
        i, first_visible = next(filter(
            lambda t: t[1].psy.ax.get_visible(),
            enumerate(self.plotter_arrays)))
        if arr is None or not arr.psy.ax.get_visible():  # array isn't plotted
            return
        elif arr is first_visible:
            p = psy.Project(self.plotter_arrays)
            p.unshare(keys='grouper', draw=False)
            p[i + 1:].share(keys='grouper', draw=False)
        arr.psy.ax.set_visible(False)
        if arr is self.arrays[0]:
            pass
        self.resize_axes([ax for ax in self.axes if ax.get_visible()])
        self.group_plots()

    def show_array(self, name):
        """Show the variable of the given `name`

        Parameters
        ----------
        name: str
            The variable name"""
        arrays = self.plotter_arrays
        arr = next(iter(arrays(name=name)), None)
        key, first_invisibles = next(
            groupby(arrays, lambda arr: arr.psy.ax.get_visible()))
        if key:  # first plot is visible
            first_invisibles = []

        if arr is None or arr.psy.ax.get_visible():  # array isn't plotted
            return
        elif any(arr is invisible_arr for invisible_arr in first_invisibles):
            i = next(i for i, a in enumerate(arrays) if a.name == name)
            p = psy.Project(arrays)
            p.unshare(keys='grouper', draw=False)
            p[i:].share(keys='grouper', draw=False)
        arr.psy.ax.set_visible(True)
        self.resize_axes([ax for ax in self.axes if ax.get_visible()])
        self.group_plots()


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

    @property
    def arrays(self):
        return self.plotter_arrays[0]

    def group_plots(self, height):
        pass

    def is_visible(self, arr):
        """Check if the given `arr` is shown"""
        return arr.name in self.plotter_arrays[0].names

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

    def hide_array(self, name):
        """Hide the variable of the given `name`

        Parameters
        ----------
        name: str
            The variable name"""
        i, arr = next(((i, arr) for i, arr in enumerate(self.arrays)
                       if arr.name == name), (None, None))
        plotter = self.plotters[0]
        v = plotter['plot']
        if v is None or isinstance(v, six.string_types):
            v = [v] * len(self.arrays)
        if arr is None or v[i] is None:  # array isn't plotted
            return
        v[i] = None
        plotter.update(plot=v, force=True)

    def show_array(self, name):
        """Show the variable of the given `name`

        Parameters
        ----------
        name: str
            The variable name"""
        i, arr = next(((i, arr) for i, arr in enumerate(self.arrays)
                       if arr.name == name), (None, None))
        plotter = self.plotters[0]
        v = plotter['plot']
        if v is None or isinstance(v, six.string_types):
            v = [v] * len(self.arrays)
        if arr is None or v[i] is not None:  # array is plotted
            return
        v[i] = '-'
        plotter.update(plot=v, force=True)


strat_groupers = {
    'all_in_one': StratAllInOne,
    'percentages': StratPercentages,
    'default': StratGroup}
