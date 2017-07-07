"""plotters module of the psy-strat psyplot plugin

This module defines the plotters for the psy-strat package.
"""
from __future__ import division
import textwrap
from psyplot.plotter import Formatoption, DictFormatoption
import six
from psy_simple.plotters import LinePlotter
from psy_simple.base import (
    TextBase, label_props, label_size, label_weight, Title)
import numpy as np

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
    tuple (float ``y``, str ``s``)
        A tuple of length 2, where the first parameter ``0<=y<=1`` determines
        the distance of the bar to the top y-axis and the second is the title
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
            xstart = self.y_px
        else:
            xstart = self.y_px * np.tan(self.angle * np.pi / 180.)
        tr = self.ax.figure.transFigure.inverted()
        xstart = tr.transform((xstart, self.y_px))[0]
        self.texts.append(
            self.ax.text(xstart + (self.x0 + self.x1) / 2.0,
                         self.top + self.y,
                         self.replace(value[1], self.data),
                         ha='center', va='center',
                         transform=self.ax.figure.transFigure,
                         bbox=dict(facecolor='w', edgecolor='none')))

    def create_annotation(self):
        """Annotate from the left to the right axes"""
        arm = self.y_px / np.sin(self.angle * np.pi / 180.)
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
        y, s = value
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
        self.y = y * this_bbox.height
        self.y_px = (tr.transform((x0, top + self.y))[1] -
                     tr.transform((x0, top))[1])
        self.top = top
        self.angle = self.titleprops.value.get('rotation', 45)

    def onresize(self, event):
        if self.shared:
            self.update(self.value)

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

    @property
    def value2pickle(self):
        """Return the current axis colors"""
        return {key: s.get_linestyle() for key, s in self.ax.spines.items()}

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


class MeasurementLines(Formatoption):
    """
    Draw lines at the measurement locations

    Possible types
    --------------
    None
        Don't draw any lines
    color
        The color of the lines
    """

    default = None

    artists = None

    dependencies = ['transpose', 'xlim', 'plot']

    def update(self, value):
        self.remove()
        if value is None:
            return
        get_y = self.transpose.get_y
        ys = np.unique(np.concatenate([get_y(arr) for arr in self.iter_data]))
        if self.plot.value is not None:
            kws = {'zorder': self.plot._plot[0].get_zorder() - 0.2}
        else:
            kws = {}
        self.artists = self.ax.hlines(ys, *self.xlim.range, color=value, **kws)

    def remove(self):
        if self.artists is not None:
            self.artists.remove()
            self.artists = None

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
    hlines = MeasurementLines('hlines')
