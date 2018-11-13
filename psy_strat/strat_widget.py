"""Module for a widget for stratigraphic plots

This module defines the :class:`StratPlotsWidget` class that can be used to
manage stratigraphic plots. It is designed as a plugin for the
:class:`psyplot_gui.main.MainWindow` class"""
import sys
from itertools import chain
from psyplot_gui.compat.qtcompat import (
    QWidget, Qt, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QCheckBox, QAbstractItemView)
from psyplot_gui.common import DockMixin
import psyplot.project as psy
from psyplot.utils import unique_everseen


def get_stratplots_widgets(mainwindow=None):
    """Get the :class:`StraditizerWidgets` from the psyplot GUI mainwindow"""
    if mainwindow is None:
        from psyplot_gui.main import mainwindow
    if mainwindow is None:
        raise NotImplementedError(
            "Not running in interactive psyplot GUI!")
    try:
        stratplots = mainwindow.plugins[
            'psy_strat.strat_widget:StratPlotsWidget:stratplots']
    except KeyError:
        raise KeyError('psy_strat not implemented as a GUI plugin!')
    return stratplots


class GrouperItem(QTreeWidgetItem):
    """An item whose contents is filled by a StratGrouper

    This item is automatically initialized by an instance of
    :class:`psy_strat.stratplot.StratGrouper`"""

    def __init__(self, grouper, tree, *args, **kwargs):
        super(QTreeWidgetItem, self).__init__(*args, **kwargs)
        self.grouper = grouper
        self.tree = tree
        self.setText(0, grouper.group)

    def add_array_children(self):
        arrays = self.grouper.arrays
        last = len(arrays) - 1
        group = self.grouper.group
        for i, arr in enumerate(arrays):
            child = QTreeWidgetItem(0)
            self.addChild(child)
            # variable name
            child.setText(0, str(arr.name))
            # arrow buttons
            child.setText(1, u'⇧' if i else '')
            child.setText(2, u'⇩' if i < last else '')
            # checkbox
            cb = QCheckBox()
            cb.setChecked(self.grouper.is_visible(arr))
            cb.stateChanged.connect(self.show_or_hide_func(arr.name))
            self.tree.setItemWidget(child, 3, cb)
            # mean
            child.setText(4, '%1.3f' % arr.mean().values)
            # min
            child.setText(5, '%1.3f' % arr.min().values)
            # max
            child.setText(6, '%1.3f' % arr.max().values)
            # group
            if arr.group != group:
                child.setText(7, str(arr.group))

    def show_or_hide_func(self, name):
        """Create a function that displays or hides the plot for an array"""
        def func(state):
            if state == Qt.Checked:
                self.grouper.show_array(name)
            else:
                self.grouper.hide_array(name)
            self.grouper.figure.canvas.draw()
        return func


class StratPlotsWidget(QWidget, DockMixin):
    """A widget for managing the stratigraphic plots from the psy-strat package
    """

    #: The title of the widget
    title = 'Stratigraphic plots'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    @property
    def stratplotter_cls(self):
        """The :class:`psy_strat.plotters.StratPlotter` class if it's
        module has already been imported. Otherwise None."""
        if 'psy_strat.plotters' not in sys.modules:
            return None
        from psy_strat.plotters import StratPlotter, BarStratPlotter
        return (StratPlotter, BarStratPlotter)

    @property
    def hidden(self):
        """True if there is no :class:`psy_strat.plotter.StratPlotter` in the
        current main project"""
        return self.stratplotter_cls is None or not bool(psy.gcp(True)(
            self.stratplotter_cls))

    def __init__(self, *args, **kwargs):
        super(StratPlotsWidget, self).__init__(*args, **kwargs)
        vbox = QVBoxLayout()
        self.tabs = QTabWidget(parent=self)
        self.trees = {}
        self.groupers = {}

        vbox.addWidget(self.tabs)
        self.setLayout(vbox)
        psy.Project.oncpchange.connect(self.update_trees_from_project)

    def update_trees_from_project(self, project):
        """Add a new QTreeWidget from the main project"""
        # do nothing for subprojects and if the StratPlotter has not yet been
        # imported
        if not project.is_main or self.stratplotter_cls is None:
            return
        from psy_strat.stratplot import strat_groupers
        project = project(self.stratplotter_cls)
        datasets = project.datasets
        fnames = project.dsnames_map
        for num in set(self.groupers).difference(datasets):
            del self.groupers[num]
            tree = self.trees.pop(num)
            self.tabs.removeTab(self.tabs.indexOf(tree))
        for num in set(datasets).difference(self.groupers):
            ds = datasets[num]
            ds_arr_names = [
                arr.psy.arr_name for i, arr in enumerate(project)
                if num in project[i:i+1].datasets]
            arrs = project(arr_name=ds_arr_names)
            groupers = []
            for group in unique_everseen(
                    arr.attrs['maingroup'] for arr in arrs):
                arrays = project(maingroup=group)
                identifier = ds[group].identifier
                grouper_cls = strat_groupers[identifier]
                groupers.append(grouper_cls(arrays, use_weakref=True))
            title = 'Dataset %i' % num
            if fnames[num]:
                title += ': ' + fnames[num]
            self.add_tree(groupers, title)
        if self.hidden:
            self.hide_plugin()

    def move_selected_children(self, child, col):
        if col not in [1, 2] or child.parent() is None:
            return
        top = child.parent()
        selected = chain([child], top.tree.selectedItems())
        up = col == 1
        move = -1 if up else 1
        children = sorted(
            unique_everseen(
                [child for child in selected if child.parent() is top],
                key=top.indexOfChild),
            key=top.indexOfChild, reverse=not up)
        current_indices = list(map(top.indexOfChild, children))
        last = top.childCount() - 1
        for current, child in zip(current_indices, children):
            if ((up and current == 0) or (not up and current == last)):
                return
            cb = top.tree.itemWidget(child, 3)
            checked = cb.isChecked()
            top.takeChild(current)
            if up:
                top.insertChild(current + move, child)
            else:
                if current == last - 1:
                    top.addChild(child)
                else:
                    top.insertChild(current + move, child)
            cb = QCheckBox()
            cb.setChecked(checked)
            cb.stateChanged.connect(top.show_or_hide_func(child.text(0)))
            top.tree.setItemWidget(child, 3, cb)
        for child in children:
            child.setSelected(True)
        for i, child in enumerate(map(top.child, range(last+1))):
            child.setText(1, u'⇧' if i > 0 else '')
            child.setText(2, u'⇩' if i < last else '')
        top.grouper.reorder(
            [child.text(0) for child in map(top.child,
                                            range(top.childCount()))])
        top.grouper.figure.canvas.draw()

    def add_tree(self, groupers, title=None):
        """Add a new QTreeWidget to the :attr:`tabs` widget"""
        tree = QTreeWidget(parent=self)
        tree.setColumnCount(7)
        tree.setHeaderLabels(
            ['Name', '', '', 'Visible', 'mean', 'min', 'max', 'Group'])
        ds = groupers[0].arrays[0].psy.base
        tree.itemClicked.connect(self.move_selected_children)
        tree.setSelectionMode(QAbstractItemView.MultiSelection)

        # fill the tree
        for grouper in groupers:
            top = GrouperItem(grouper, tree, 0)
            tree.addTopLevelItem(top)
            top.add_array_children()

        self.tabs.addTab(tree, title or 'Dataset %i' % ds.psy.num)
        tree.expandAll()
        for i in range(7):
            tree.resizeColumnToContents(i)
        self.show_plugin()
        self.groupers[ds.psy.num] = groupers
        self.trees[ds.psy.num] = tree
