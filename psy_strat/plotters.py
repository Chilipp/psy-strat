"""plotters module of the psy-strat psyplot plugin

This module defines the plotters for the psy-strat package.
"""
from __future__ import division
import textwrap
from itertools import cycle
from psyplot.data import safe_list
from psyplot.plotter import (
    Formatoption, DictFormatoption, BEFOREPLOTTING, START)
import six
import psy_simple.plotters as psyps
from psy_simple.base import (
    TextBase, label_props, label_size, label_weight, Title)
import numpy as np

# -----------------------------------------------------------------------------
# ---------------------------- Formatoptions ----------------------------------
# -----------------------------------------------------------------------------


class TitleLoc(Formatoption):
    """
    Specify the position of the axes title

    Parameters
    ----------
    str
        The position the axes title

        center
            In the center of the axes (the standard way)
        left
            At the left corner
        right
            At the right corner"""

    group = Title.group

    name = 'Location of the axes title'

    def update(self, value):
        # value is considered in title formatoption
        pass


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
    title_loc: The location of the title
    figtitle, titlesize, titleweight, titleprops"""
    # Reimplemented to plot the title on the left side

    dependencies = Title.dependencies + ['title_loc']

    def initialize_plot(self, value):
        arr = self.data
        self.texts = [self.ax.set_title(
            self.replace(value, arr, attrs=self.enhanced_attrs),
            loc=self.title_loc.value)]

    def update(self, value):
        for t in self.texts:
            t.set_text('')
        self.initialize_plot(value)


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
        of the group. `y` must be given relative to the axes height.
    """

    texts = []

    annotations = []

    value2share = None

    name = 'Group the axes'

    dependencies = ['titleprops', 'title']

    def initialize_plot(self, value):
        self.texts = []
        self.annotations = []
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
        self.create_annotations()

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
                         ha='center', va='bottom',
                         transform=self.ax.figure.transFigure,
                         bbox=dict(facecolor='w', edgecolor='none')))

    def create_annotations(self):
        """Annotate from the left to the right axes"""
        fmtos = [self] + list(self.shared)
        boxes = [fmto.ax.get_position() for fmto in fmtos]
        fmto0 = min(zip(fmtos, boxes), key=lambda t: t[1].x0)[0]
        fmto1 = max(zip(fmtos, boxes), key=lambda t: t[1].x0)[0]
        t0 = fmto0.ax._left_title
        t1 = fmto1.ax._left_title
        kws = dict(
            zorder=self.texts[0].get_zorder() - 0.1,
            arrowprops=dict(
                arrowstyle="-",
                connectionstyle="angle,angleA=%1.3f,angleB=0" % self.angle))
        ax = self.ax
        self.annotations = [
            ax.annotate("", (0.0, 0.5), (0.0, 0.0), self.texts[0], t0, **kws),
            ax.annotate("", (1.0, 0.5), (0.0, 0.0), self.texts[0], t1, **kws)]

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
        if annotation:
            for a in self.annotations:
                a.remove()
            self.annotations.clear()


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


class ExagFactor(Formatoption):
    """
    The exaggerations factor

    Possible types
    --------------
    float
        The factor by how much the data should be exaggerated

    See Also
    --------
    exag_color, exag
    """

    priority = BEFOREPLOTTING

    name = 'Exaggeration factor'

    def update(self, value):
        # Does nothing
        pass


class ExagPlot(psyps.LinePlot):

    __doc__ = psyps.LinePlot.__doc__

    dependencies = ['exag_factor']

    def plot_arr(self, arr, *args, **kwargs):
        return super(ExagPlot, self).plot_arr(
            arr * self.exag_factor.value, *args, **kwargs)


class Occurences(Formatoption):
    """
    Specify the range for occurences

    This formatoption can be used to specify a minimum and a maximum value.
    The parts of the data that fall into this range will be considered as an
    occurence, set to 0 and marked by the :attr:`occurence_value` formatoption

    Possible types
    --------------
    None
        Do not mark anything as an occurence
    float
        Anything below the given number will be considered as an occurence
    tuple of floats ``(vmin, vmax)``
        The minimum and maximum value. Anything between `vmin` and `vmax` will
        be marked as a occurence

    See Also
    --------
    occurence_marker, occurence_value
    """

    name = 'Occurences range'

    priority = START

    children = ['maskless', 'maskleq', 'maskgreater', 'maskgeq']

    def update(self, value):
        if value is None:
            return
        self.occurences = []
        try:
            value = list(value)
        except TypeError:
            value = [-np.inf, value]
        vmin, vmax = value
        for i, arr in enumerate(self.iter_data):
            new_arr = arr.copy(True)
            mask = (arr.values >= vmin) & (arr.values <= vmax)
            self.occurences.append(mask)
            new_arr.values[mask] = 0
            self.set_data(new_arr, i)


class OccurenceMarker(Formatoption):
    """
    Specify the marker for occurences

    This formatoption can be used to define the marker style for occurences.

    Possible types
    --------------
    None
        Use the mean of the axes limits
    float
        Specify the x-value for an occurence
    list of floats
        Specify the x-value for an occurence for each array explicitly

    See Also
    --------
    occurences, occurence_value
    """

    name = 'Marker for the occurences'

    def update(self, value):
        # Does nothing, value is used in :meth:`OccurencePlot.update`
        pass


class OccurencePlot(Formatoption):
    """
    Specify the value to use for occurences in the plot

    This formatoption can be used to define where the occurence marker should
    be placed.

    Possible types
    --------------
    None
        Use the mean of the axes limits
    float
        Specify the x-value for an occurence
    list of floats
        Specify the x-value for an occurence for each array explicitly

    See Also
    --------
    occurences, occurence_marker
    """

    dependencies = ['occurences', 'xlim', 'occurence_marker', 'color',
                    'transpose']

    _artists = None

    name = 'Occurence plot value'

    def update(self, value):
        self.remove()
        if self.occurences.value is None:
            return
        elif value is None:
            value = np.mean(self.xlim.range)
        self._artists = artists = []
        for mask, arr, val, color, marker in zip(
                self.occurences.occurences, self.iter_data,
                cycle(safe_list(value)), self.color.colors,
                cycle(self.occurence_marker.value)):
            x = arr[arr.dims[-1]].values[mask]
            y = [val] * len(x)
            if self.transpose.value:
                x, y = y, x
            artists.extend(
                self.ax.plot(x, y, marker=marker, color=color, lw=0))

    def remove(self):
        if self._artists is not None:
            for a in self._artists:
                try:
                    a.remove()
                except ValueError:
                    pass
            del self._artists


# -----------------------------------------------------------------------------
# ------------------------------ Plotters -------------------------------------
# -----------------------------------------------------------------------------


class StratPlotter(psyps.LinePlotter):
    """A plotter for stratigraphic diagrams"""

    _rcparams_string = ['plotter.strat.']

    axislinestyle = AxisLineStyle('axislinestyle')
    title_loc = TitleLoc('title_loc')
    title = LeftTitle('title')
    title_wrap = TitleWrap('title_wrap')
    grouper = AxesGrouper('grouper')
    grouperprops = label_props(grouper)
    grouperweight = label_weight(grouper)
    groupersize = label_size(grouper)
    hlines = MeasurementLines('hlines')
    exag_color = psyps.LineColors('exag_color')
    exag_factor = ExagFactor('exag_factor')
    exag = ExagPlot('exag', color='exag_color')

    # occurences
    occurences = Occurences('occurences')
    occurence_marker = OccurenceMarker('occurence_marker')
    occurence_value = OccurencePlot('occurence_value')


class BarStratPlotter(psyps.BarPlotter):
    """A bar plotter for stratigraphic diagrams"""

    _rcparams_string = ['plotter.strat.', 'plotter.barstrat.']

    axislinestyle = AxisLineStyle('axislinestyle')
    title_loc = TitleLoc('title_loc')
    title = LeftTitle('title')
    title_wrap = TitleWrap('title_wrap')
    grouper = AxesGrouper('grouper')
    grouperprops = label_props(grouper)
    grouperweight = label_weight(grouper)
    groupersize = label_size(grouper)
    hlines = MeasurementLines('hlines')
    exag_color = psyps.LineColors('exag_color')
    exag_factor = ExagFactor('exag_factor')
    exag = ExagPlot('exag', color='exag_color')

    # occurences
    occurences = Occurences('occurences')
    occurence_marker = OccurenceMarker('occurence_marker')
    occurence_value = OccurencePlot('occurence_value')
