"""Module to create new stratigraphic plots

This module defines the :func:`stratplot` function that can be used to create
stratigraphic plots such as pollen diagrams
"""
from __future__ import division
import weakref
import six
from itertools import groupby, chain, islice
import matplotlib as mpl
import matplotlib.transforms as mt
from collections import defaultdict
import psyplot
from psyplot.utils import DefaultOrderedDict
import xarray as xr
import numpy as np
from psy_strat.plotters import StratPlotter, BarStratPlotter
from psyplot.data import ArrayList
import psyplot.project as psy
from docrep import DocstringProcessor

docstrings = DocstringProcessor()


gui_plugin = 'psy_strat.strat_widget:StratPlotsWidget:stratplots'


NOGROUP = 'nogroup'


def _no_grouper(col):
    """Return an empty string to disable the grouping"""
    return NOGROUP


def stratplot(df, group_func=None, formatoptions=None, ax=None,
              thresh=0.01, percentages=[], exclude=[],
              widths=None, calculate_percentages=True,
              min_percentage=20.0, trunc_height=0.3, fig=None, all_in_one=[],
              stacked=[], summed=[], use_bars=False, subgroups={}):
    """Visualize a dataframe as a stratigraphic plot

    This functions takes a :class:`pandas.DataFrame` and transforms it to a
    stratigraphic plot. The columns in the DataFrame may be grouped together
    using the `group_func` and the widths per group should then be specified.
    This function uses matplotlib axes for each subdiagram that all share a
    common vertical axes, the index of `df`. The variables are managed in the
    order of occurence in the input `df` but, however, are grouped together
    depending on the `group_func`.

    The default is to plot every variable in `df` into separete line plots
    that line up vertically. You can use the `percentages` parameter for area
    plots, the `all_in_one` parameter for groups that should be all in one
    single plot (i.e. axes) and the `stacked` parameter for stacked plots.

    Parameters
    ----------
    df: pandas.DataFrame
        The dataframe containing the data to plot.
    group_func: function
        A function that groups the columns in the input `df` together. It must
        accept the name of a column and return the corresponding group name::

            def group_func(col_name: str):
                return "name of it's group"

        If this parameter is not specified, each column will be assigned to the
        `'nogroup'` group that can then be used in the other parameters, such
        as `formatoptions` and `percentages`. Each group may also be divided
        into `subgroups` (see below), in this case, the `group_func` should
        return the corresponding subgroup.
    formatoptions: dict
        The formatoption for each group. Depending on the chosen plot method,
        this contains the formatoptions for the psyplot plotter.
    ax: matplotlib.axes.Axes
        The matplotlib axes to plot on. New axes will be created that cover all
        the space of the given axes.
        If this parameter is not specified and `fig` is None, a new matplotlib
        figure is created with a new matplotlib axes.
    thresh: float
        A minimum number between 0 and 100 (by default 1%) that a
        `percentages` column has to fullfil in order to be included in the
        plot. If a variable is always below this threshold, it will not be
        included in the figure
    percentages: list of str or bool
        The group names (see `group_func`) that represent percentage values.
        This variables will be visualized using an area plot and can be
        rescaled to sum up to 100% using the `calculate_percentages` parameter.
        This parameter can also be set to True if all groups shall be
        considered as percentage data
    exclude: list of str
        Either group names of column names in `df` that should be excluded in
        the plot
    widths: dict
        A mapping from group name to it's relative width in the plot. The
        values of this mapping should some up to 1, e.g.::

            widths = {'group1': 0.3, 'group2': 0.5, 'group3': 0.2}
    calculate_percentages: bool or list of str
        If True, rescale the groups mentioned in the `percentages` parameter
        to sum up to 100%. In case of a list of str, this parameter represents
        the group (or variable) names that shall be used for the normalization
    min_percentage: float
        The minimum percentage (between 0 and 100) that should be covered by
        variables displaying `percentages` data. Each plot in one of the
        `percentages` groups will have at least have a xlim from 0 to
        `min_percentage`
    trunc_height: float
        A float between 0 and 1. The fraction of the `ax` that should be
        reserved for the group titles.
    fig: matplotlib.Figure
        The matplotlib figure to draw the plot on. If neither `ax` nor `fig` is
        specified, a new figure will be created.
    all_in_one: list of str
        The groups mentioned in this parameter will all be plotted in one
        single axes whereas the default is to plot each variable in a separate
        plot
    stacked: list of str
        The groups mentioned in this parameter will all be plotted in one
        single axes, stacked onto each other
    summed: list of str
        The groups (or subgroups) mentioned in this parameter will be summed
        and an extra plot will be appended to the right of the stratigraphic
        diagram
    use_bars: list of str or bool
        The variables specified in this parameter (or all variables if
        `use_bars` is ``True``) will be visualized by a bar diagram, instead
        of a line or area plot.
    subgroups: dict
        A mapping from group name to a list of subgroups, e.g.::

            subgroups = {'Pollen': ['Trees', 'Shrubs']}

        to divide an overarching group into subgroups.

    Returns
    -------
    psyplot.project.Project
        The newly created psyplot subproject that contains the displayed data
    list of :class:`StratGroup`
        The groupers that manage the different variables. There is one
        grouper per group"""
    import psyplot.project as psy
    import matplotlib.pyplot as plt
    if group_func is None:
        group_func = _no_grouper
    groups = DefaultOrderedDict(list)
    # we invert subgroups here
    subgroup2group = dict(chain.from_iterable(
        ((sub, group) for sub in subs)
        for group, subs in subgroups.items()))
    cols = {}
    for col in df.columns:
        group = group_func(col)
        group = subgroup2group.get(group, group)
        groups[group].append(col)
        cols[col] = group

    # Setup percentages
    if isinstance(percentages, six.string_types):
        percentages = [percentages]
    try:
        percentages = list(percentages)
    except TypeError:
        percentages = list(groups) if percentages else []

    formatoptions = formatoptions or {}
    if calculate_percentages and set(percentages).intersection(groups):
        df = df.copy(True)
        for group in set(percentages).intersection(groups):
            members = groups[group]
            try:
                calculate_percentages = list(calculate_percentages)
            except TypeError:
                norm_members = members
            else:
                norm_members = list(set(chain.from_iterable(
                    [var] if var in df.columns else groups[var]
                    for var in calculate_percentages)))

            df[members] *= 100. / np.tile(
                df[norm_members].fillna(0).sum(axis=1)[:, np.newaxis],
                (1, len(members)))
    if summed:
        try:
            summed = list(summed)
        except TypeError:
            summed = list(groups)
        stacked.append('Summed')
        groups['Summed'] = [g + '_summed' for g in summed]
        if widths:
            widths.setdefault('Summed', 0.2)
        formatoptions.setdefault('Summed', {}).setdefault(
            'legendlabels', '%(long_name)s')
        formatoptions['Summed'].setdefault('title', '')
    else:
        summed = []

    widths = widths or defaultdict(
        lambda: 1. / (len(set(groups).difference(percentages)) or 1))

    # Setup use_bars
    if isinstance(use_bars, six.string_types):
        use_bars = [use_bars]
    try:
        use_bars = list(use_bars)
    except TypeError:
        use_bars = list(groups) if use_bars else []

    # NOTE: we create the Dataset manually instead of using
    # xarray.Dataset.from_dataframe becuase that is much faster
    idx = df.index.name or 'y'
    ds = xr.Dataset(
        {col: xr.Variable((idx, ), df[col]) for col in df.columns},
        {idx: xr.Variable((idx, ), df.index)})
    for var, varo in ds.variables.items():
        if var not in ds.coords:
            varo.attrs['group'] = group_func(var)
            varo.attrs['maingroup'] = cols[var]
    for group in summed:
        variables = [var for var, varo in ds.variables.items()
                     if varo.attrs.get('group') == group]
        ds[group + '_summed'] = xr.Variable(
            (idx, ), df[variables].sum(axis=1).values,
            attrs={'long_name': group, 'group': 'Summed',
                   'maingroup': 'Summed'})

        cols[group + '_summed'] = 'Summed'

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
    orig_height = bbox.height
    height = orig_height * (1 - trunc_height)
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
            elif group in stacked:
                identifier = 'stacked'
            elif group in percentages:
                identifier = 'percentages'
            else:
                identifier = 'default'
            grouper_cls = strat_groupers[identifier]
            grouper = grouper_cls.from_dataset(
                fig, mt.Bbox.from_bounds(x, y0, w, height),
                ds, variables, fmt=dict(formatoptions.get(group, {})),
                project=mp, ax0=ax0, use_bars=use_bars, group=group)
            if identifier == 'percentages':
                resize = False
                for plotter in grouper.plotters:
                    if plotter.ax.get_xlim()[1] < min_percentage:
                        plotter.update(xlim=(0, min_percentage))
                        resize = True
                if resize:
                    grouper.resize_axes(grouper.axes)
            if group != NOGROUP:
                grouper.group_plots(trunc_height / height)
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
    # invert the vertical axis
    ax0.invert_yaxis()

    sp = psy.gcp(True)(arr_name=arr_names)
    sp[0].psy.update(
        ylabel='%(name)s', ytickprops={'left': True, 'labelleft': True},
        draw=False)
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
    return sp, groupers


class StratGroup(object):
    """Base class for visualizing stratigraphic plots"""

    #: list of weakref. Weak references to the created arrays
    _refs = []

    _arrays = None

    _plotter_arrays = None

    grouper_height = None

    #: The default formatoptions for the plots
    default_fmt = {
        'ytickprops': {'left': False, 'labelleft': False},
        }

    bar_default_fmt = default_fmt.copy()
    bar_default_fmt['categorical'] = False

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

    def __init__(self, arrays, bbox=None, use_weakref=True, group=None):
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
        group: str
            The groupname of this grouper. If not given, it will be taken from
            the ``'maingroup'`` attribute of the first array
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
        self.group = group or arrays[0].attrs.get('maingroup')

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
        """Group the variables visually

        Parameters
        ----------
        height: float
            The height of the grouper. If not specified, the previous
            :attr:`grouper_height` attribute will be used"""
        for plotter in (plotter for plotter in self.plotters
                        if plotter.ax.get_visible() and
                        not plotter.grouper.shared_by):
            height = height or self.grouper_height
            if height is None and plotter['grouper']:
                height = plotter['grouper'][0]
            elif height is None:
                return
            self.grouper_height = height
            plotter.update(grouper=(height, '%(group)s'),
                           draw=False, force=True)
            for fmto in plotter.grouper.shared:
                with fmto.plotter.no_validation:
                    fmto.plotter['grouper'] = (height, '%(group)s')

    @property
    def figure(self):
        """The figure that contains the plots"""
        return self.axes[0].figure

    def is_visible(self, arr):
        """Check if the given `arr` is shown"""
        return arr.psy.plotter.ax.get_visible()

    @classmethod
    @docstrings.get_sectionsf('StratGroup.from_dataset',
                              sections=['Parameters', 'Returns'])
    def from_dataset(cls, fig, bbox, ds, variables, fmt=None, project=None,
                     ax0=None, use_bars=False, group=None):
        """
        Create :class:`StratGroup` while creating a stratigraphic plot

        Create a stratigraphic plot within the given `bbox` of `fig`.

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
        use_bars: bool
            Whether to use a bar plot or a line/area plot

        Returns
        -------
        StratGroup
            The newly created instance with the arrays
        """
        if ax0 is None:
            ax0 = fig.add_axes(bbox.from_bounds(*bbox.bounds), label='ax0')
            axes = [ax0] + [fig.add_axes(bbox.from_bounds(*bbox.bounds),
                                         sharey=ax0, label='ax%i' % i)
                            for i in range(1, len(variables))]
        else:
            axes = [fig.add_axes(bbox.from_bounds(*bbox.bounds),
                                 sharey=ax0, label='ax%i' % i)
                    for i in range(len(variables))]
        grouped = DefaultOrderedDict(list)
        for name in variables:
            grouped[ds[name].attrs.get('group', 'group')].append(name)
        # Use group specific bars
        if use_bars:
            try:
                use_bars = list(use_bars)
            except TypeError:
                use_bars = list(grouped)
        else:
            use_bars = []
        sp = None
        axes_it = iter(axes)
        for subgroup, names in grouped.items():
            formatoptions = dict(fmt or {})
            if subgroup in use_bars or group in use_bars:
                plotter_cls = BarStratPlotter
                defaults = cls.bar_default_fmt
            else:
                plotter_cls = StratPlotter
                defaults = cls.default_fmt
            for key, val in six.iteritems(defaults):
                formatoptions.setdefault(key, val)
            sp2 = psy.Project()._add_data(
                plotter_cls, ds, name=names, draw=False, fmt=formatoptions,
                prefer_list=False, ax=islice(axes_it, len(names)),
                share='grouper', attrs=dict(maingroup=group))
            if project is not None:
                project.extend(sp2, new_name=True)
            sp = sp2 if sp is None else sp + sp2
        ret = cls(list(sp), bbox, use_weakref=project is not None,
                  group=group)
        ret.resize_axes(axes)
        return ret

    def hide_array(self, name):
        """Hide the variable of the given `name`

        Parameters
        ----------
        name: str
            The variable name"""
        arr = next(iter(self.plotter_arrays(name=name)), None)
        if arr is None:
            return
        group = arr.group
        i, first_visible = next(filter(
            lambda t: t[1].psy.ax.get_visible() and t[1].group == group,
            enumerate(self.plotter_arrays)))
        if arr is None or not arr.psy.ax.get_visible():  # array isn't plotted
            return
        elif arr is first_visible:
            p = psy.Project(self.plotter_arrays)(group=group)
            p.unshare(keys='grouper', draw=False)
            p(name=set(p.names) - {name}).share(keys='grouper', draw=False)
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
        if arr is None:
            return
        group = arr.group
        key, first_invisibles = next(
            groupby(filter(lambda a: a.group == group, arrays),
                    lambda arr: arr.psy.ax.get_visible()))
        if key:  # first plot is visible
            first_invisibles = []

        if arr.psy.ax.get_visible():  # array isn't plotted
            return
        elif any(arr is invisible_arr for invisible_arr in first_invisibles):
            p = psy.Project(arrays)(group=group)
            p.unshare(keys='grouper', draw=False)
#            i = next(i for i, a in enumerate(p) if a.name == name)
            p(name=set(p.names) - {name}).share(arr, keys='grouper',
                                                draw=False)
        arr.psy.ax.set_visible(True)
        self.resize_axes([ax for ax in self.axes if ax.get_visible()])
        self.group_plots()

    def reorder(self, names):
        """Reorder the plot objects

        Parameters
        ----------
        names: list of str
            The variable names that should be the first"""
        arrays = self._plotter_arrays or self._refs
        old = list(arrays)
        old_da = list(self.plotter_arrays)
        project = self.plotters[0].project
        if project is not None:
            project = project.main
            i = project.arr_names.index(old_da[0].psy.arr_name)
            arr_names = project.arr_names[i:i+len(arrays)]
            reorder_project = arr_names == self.arr_names
        arrays.clear()
        for name in names:
            arr = next((old[i] for i, arr in enumerate(old_da)
                        if str(arr.name) == name), None)
            if arr is not None:
                arrays.append(arr)
        # now add the ones that are not mentioned in `names`
        for i, arr in enumerate(old_da):
            if str(arr.name) not in names:
                arrays.append(old[i])
        if project is not None and reorder_project:
            project[i:i+len(arrays)] = self.plotter_arrays
            if project.is_csp or project.is_cmp:
                project.oncpchange.emit(project)
        self.resize_axes([ax for ax in self.axes if ax.get_visible()])
        self.plotter_arrays.update(force=['grouper'], draw=False)


class StratPercentages(StratGroup):
    """A :class:`StratGroup` for percentages plots"""

    default_fmt = StratGroup.default_fmt.copy()
    default_fmt['xlim'] = (0, 'rounded')
    default_fmt['xticks'] = np.arange(10, 100, 20)

    bar_default_fmt = default_fmt.copy()
    bar_default_fmt['categorical'] = False

    default_fmt['plot'] = 'areax'

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

    bar_default_fmt = default_fmt.copy()
    bar_default_fmt['categorical'] = False

    @property
    def arrays(self):
        return self.plotter_arrays[0]

    def group_plots(self, height):
        """Reimplemented to do nothing because all variables are in one axes
        """
        pass

    def is_visible(self, arr):
        """Check if the given `arr` is shown"""
        return arr.name in self.plotter_arrays[0].names

    @classmethod
    @docstrings.dedent
    def from_dataset(cls, fig, bbox, ds, variables, fmt=None, project=None,
                     ax0=None, use_bars=False, group=None):
        """
        Create :class:`StratGroup` while creating a stratigraphic plot

        Create a stratigraphic plot within the given `bbox` of `fig`.

        Parameters
        ----------
        %(StratGroup.from_dataset.parameters)s

        Returns
        -------
        %(StratGroup.from_dataset.returns)s
        """
        fmt = fmt or {}
        if use_bars:
            try:
                use_bars = list(iter(use_bars))
            except TypeError:
                use_bars = True
            else:
                use_bars = group in use_bars
        defaults = cls.bar_default_fmt if use_bars else cls.default_fmt
        for key, val in six.iteritems(defaults):
            fmt.setdefault(key, val)
        if ax0 is None:
            ax = fig.add_axes(bbox.from_bounds(*bbox.bounds), label='ax0')
        else:
            ax = fig.add_axes(bbox.from_bounds(*bbox.bounds),
                              sharey=ax0, label='ax0')
        plotter_cls = BarStratPlotter if use_bars else StratPlotter
        sp = psy.Project()._add_data(
            plotter_cls, ds, name=variables, draw=False, fmt=fmt,
            prefer_list=True, ax=ax, share='grouper',
            attrs=dict(maingroup=group))
        if project is not None:
            project.extend(sp, new_name=True)
        return cls(list(sp), bbox, use_weakref=project is not None,
                   group=group)

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
        v[i] = self.default_fmt.get('plot', '-')
        plotter.update(plot=v, force=True)

    def reorder(self, names):
        """Reorder the plot objects

        Parameters
        ----------
        mapping: dict
            A mapping from the new index to the old one"""
        plotter = self.plotters[0]
        data = plotter.data
        current = list(data)
        visibilities = list(map(self.is_visible, data))
        plot = []
        data.clear()
        ls = self.default_fmt.get('plot', '-')
        for name in names:
            i = next(i for i, arr in enumerate(current)
                     if str(arr.name) == name)
            data.append(current[i])
            plot.append((visibilities[i] and ls) or None)
        plotter.update(plot=plot, replot=True, draw=False)


class StackedGroup(StratAllInOne):
    """A grouper for stacked plots"""

    default_fmt = StratAllInOne.default_fmt.copy()
    default_fmt['plot'] = 'stacked'

    bar_default_fmt = StratAllInOne.bar_default_fmt.copy()
    bar_default_fmt['plot'] = 'stacked'


strat_groupers = {
    'all_in_one': StratAllInOne,
    'percentages': StratPercentages,
    'default': StratGroup,
    'stacked': StackedGroup}
