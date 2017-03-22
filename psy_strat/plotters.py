"""plotters module of the psy-strat psyplot plugin

This module defines the plotters for the psy-strat package.
"""
from __future__ import division
import textwrap
from collections import defaultdict
import matplotlib as mpl
from psyplot.plotter import Formatoption, DictFormatoption
import six
from psy_simple.plotters import LinePlotter
from psy_simple.base import (
    TextBase, label_props, label_size, label_weight, Title)
from psyplot.utils import DefaultOrderedDict
import xarray as xr
import numpy as np


def stratplot(df, grouper, formatoptions=None, ax=None,
              thresh=0.01, percentages=[], exclude=[],
              widths=None, calculate_percentages=True,
              min_perc=5.0, trunc_height=0.3, annot_start=0.2):
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
        ax0 = plt.subplots()[1]
        fig = ax0.figure
        bbox = ax0.get_position()
    else:
        bbox = ax.get_position()
        fig = ax.figure
        ax0 = fig.add_axes(bbox, label='ax0')
    x0 = bbox.x0
    y0 = bbox.y0
    height = bbox.height - bbox.height * trunc_height
    total_width = bbox.width
    x1 = x0 + total_width
    axes = [ax0] + [fig.add_axes(bbox.from_bounds(*bbox.bounds), sharey=ax0,
                                 label='ax%i' % i)
                    for i in range(1, len(plot_vars))]

    i = 0
    with psy.Project.block_signals:
        for group, variables in groups.items():

            variables = [v for v in variables if v in plot_vars]
            if not variables:
                continue
            width = widths[group] * total_width
            fmt = dict(formatoptions.get(group, {}))

            if group in percentages:
                def get_axwidth(ax):
                    return width * ax.get_xlim()[1] / 100.
                fmt.setdefault('plot', 'areax')
                fmt.setdefault('xlim', (0, 'rounded'))
            else:
                def get_axwidth(ax):
                    return width / len(variables)
            fmt.setdefault(
                'grouper', (annot_start, (bbox.height - height) / height,
                            '%(group)s'))
            fmt.setdefault('yticks_visible', False)
            sp = psy.plot.stratographic(ds, name=variables, fmt=fmt,
                                        ax=axes[i:i+len(variables)],
                                        draw=False,
                                        share='grouper')
            if group in percentages:
                for plotter in sp.plotters:
                    if plotter.ax.get_xlim()[1] < min_perc:
                        plotter.update(xlim=(0, min_perc), draw=False)
                width /= sum(ax.get_xlim()[1] for ax in sp.axes) / 100.
            for plotter in sp.plotters:
                w = get_axwidth(plotter.ax)
                plotter.ax.set_position([x0, y0, w, height])
                x0 += w
            sp.update(grouper=fmt['grouper'], force=True)
            if i == 0:
                sp[0].psy.update(yticks_visible=True, draw=False)
            i += len(variables)

            arr_names.extend(sp.arr_names)
        sp = psy.gcp(True)(arr_name=arr_names)
    for ax, p in sp.axes.items():
        ax_bbox = ax.get_position()
        d = {}
        if ax_bbox.x0 != x0:
            d['left'] = ':'
        if ax_bbox.x1 != x1:
            d['right'] = ':'
        p.update(axislinestyle=d, draw=False)
    psy.scp(sp)
    return sp

# -----------------------------------------------------------------------------
# ---------------------------- Formatoptions ----------------------------------
# -----------------------------------------------------------------------------


class YTicksVisibility(Formatoption):
    """
    Enable or disable the visibility of ytick labels

    Possible types
    --------------
    bool
        If True, the ticklabels are visible. Otherwise, not
    """

    group = 'ticks'

    name = 'Enable or disable the visibility of the yticks'

    def update(self, value):
        for t in self.ax.get_yticklabels():
            t.set_visible(value)


class LeftTitle(Title):
    """
    Show the title

    Set the title of the plot.
    %(replace_note)s

    Possible types
    --------------
    str
        The title for the :func:`~matplotlib.pyplot.title` function.

    Notes
    -----
    This is the title of this specific subplot! For the title of the whole
    figure, see the :attr:`figtitle` formatoption.

    See Also
    --------
    figtitle, titlesize, titleweight, titleprops"""
    # Reimplemented to plot the title on the left side

    def initialize_plot(self, value):
        arr = self.data
        self.texts = [self.ax.set_title(
            self.replace(value, arr, attrs=self.enhanced_attrs),
            loc='left')]


class TitleWrap(Formatoption):
    """
    Wrap the title automatically

    This formatoption wraps the title using :func:`textwrap.wrap`.

    Possible types
    --------------
    int
        If 0, the title will not be rapped, otherwise it will be wrapped after
        the given number of characters

    Notes
    -----
    This wraps the title after a certain amount of characters. For wrapping the
    text automatically before it leaves the plot area, use
    ``titleprops=dict(wrap=True)``
    """

    group = 'labels'

    name = 'Wrap the title'

    dependencies = ['title']

    def update(self, value):
        if value:
            for t in self.title.texts:
                t.set_text('\n'.join(textwrap.wrap(t.get_text(), value)))


class AxesGrouper(TextBase, Formatoption):
    """
    Group several axes through a bar

    This formatoption groups several plots on the same row by drawing a
    bar over them

    Possible types
    --------------
    None
        To not do anything
    tuple (float ``y0``, float ``y1``, str ``s``)
        A tuple of length 3, where the first parameter ``0<=y0<=1`` determines
        the distance of the start to the top y-axis, the second ``0<=y1<=1``
        the distance of the bar to the top y-axis and the third is the title
        of the group
    """

    texts = []

    annotation = None

    value2share = None

    name = 'Group the axes'

    dependencies = ['titleprops']

    def initialize_plot(self, value):
        self.texts = []
        super(AxesGrouper, self).initialize_plot(value)
        # redraw the annotation on resize to make sure it stays at the same
        # place as the text
        self.ax.figure.canvas.mpl_connect('resize_event', self.onresize)

    def update(self, value):
        self.remove()
        if value is None:
            return
        self.set_params(value)
        self.create_text(value)
        self.create_annotation()

    def create_text(self, value):
        if self.angle == 90:
            xstart = self.y1_px
        else:
            xstart = self.y1_px * np.tan(self.angle * np.pi / 180.)
        tr = self.ax.figure.transFigure.inverted()
        xstart = tr.transform((xstart, self.y1_px))[0]
        self.texts.append(
            self.ax.text(xstart + (self.x0 + self.x1) / 2.0,
                         self.top + self.y1,
                         self.replace(value[2], self.data),
                         ha='center', va='center',
                         transform=self.ax.figure.transFigure,
                         bbox=dict(facecolor='w', edgecolor='none')))

    def create_annotation(self):
        """Annotate from the left to the right axes"""
        arm = self.y1_px / np.sin(self.angle * np.pi / 180.)
        self.annotation = self.ax.annotate(
            "", (self.x1, self.top), (self.x0, self.top),
            'figure fraction', 'figure fraction',
            arrowprops=dict(
                arrowstyle="-",
                connectionstyle=("arc,angleA=%(angle)1.3f,angleB=%(angle)1.3f,"
                                 "armA=%(arm)1.3f,armB=%(arm)1.3f") % {
                                     'angle': self.angle, 'arm': arm}),
            zorder=self.texts[0].get_zorder() - 0.1)

    def set_params(self, value):
        """Set the parameters for the annotation and the text"""
        y0, y1, s = value
        this_bbox = self.ax.get_position()
        if not self.shared:
            x0 = this_bbox.x0
            x1 = this_bbox.x1
            top = this_bbox.y1
        else:
            boxes = [this_bbox] + [
                fmto.ax.get_position() for fmto in self.shared]
            top = max(bbox.y1 for bbox in boxes)
            x0 = min(bbox.x0 for bbox in boxes)
            x1 = max(bbox.x0 for bbox in boxes)
        self.x0 = x0
        self.x1 = x1
        tr = self.ax.figure.transFigure
        self.y1 = y1 * this_bbox.height
        self.y1_px = (tr.transform((x0, top + self.y1))[1] -
                   tr.transform((x0, top))[1])
        self.top = top
        self.angle = self.titleprops.value.get('rotation', 45)

    def onresize(self, event):
        if self.shared:
            self.update(self.value)
#            self.remove(annotation=True, text=False)
#            self.set_params(self.value)
#            self.create_annotation()

    def remove(self, annotation=True, text=True):
        if text:
            for t in self.texts[:]:
                t.remove()
                self.texts.remove(t)
        if annotation and self.annotation is not None:
            self.annotation.remove()
            del self.annotation


class AxisLineStyle(DictFormatoption):
    """
    Set the linestyle the x- and y-axes

    This formatoption sets the linestyle of the left, right, bottom and top
    axis.

    Possible types
    --------------
    dict
        Keys may be one of {'right', 'left', 'bottom', 'top'},  the values can
        be any valid linestyle or None to use the default style. The line style
        string can be one of (['solid' | 'dashed', 'dashdot', 'dotted'
        | (offset, on-off-dash-seq) | '-' | '--' | '-.' | ':' | 'None' | ' ' |
        ''])."""

    group = 'axes'

    name = 'Linestyle of x- and y-axes'

    def initialize_plot(self, value):
        positions = ['right', 'left', 'bottom', 'top']
        #: :class:`dict` storing the default linewidths
        self.default_lw = dict(zip(positions, map(
            lambda pos: self.ax.spines[pos].get_linewidth(), positions)))
        self.update(value)

    def update(self, value):
        for pos, style in six.iteritems(value):
            spine = self.ax.spines[pos]
            spine.set_linestyle(style)
            if self is not None and spine.get_linewidth() == 0.0:
                spine.set_linewidth(1.0)
            elif self is None:
                spine.set_linestyle('solid')
                spine.set_linewidth(self.default_lw[pos])

# -----------------------------------------------------------------------------
# ------------------------------ Plotters -------------------------------------
# -----------------------------------------------------------------------------


class StratPlotter(LinePlotter):

    _rcparams_string = ['plotter.strat.']

    yticks_visible = YTicksVisibility('yticks_visible')
    axislinestyle = AxisLineStyle('axislinestyle')
    title = LeftTitle('title')
    title_wrap = TitleWrap('title_wrap')
    grouper = AxesGrouper('grouper')
    grouperprops = label_props(grouper)
    grouperweight = label_weight(grouper)
    groupersize = label_size(grouper)
