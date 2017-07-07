"""Module for a widget for stratographic plots

This module defines the :class:`StratPlotsWidget` class that can be used to
manage stratographic plots. It is designed as a plugin for the
:class:`psyplot_gui.main.MainWindow` class"""
import sys
from psyplot_gui.compat.qtcompat import (
    QWidget, Qt, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QCheckBox)
from psyplot_gui.common import DockMixin
import psyplot.project as psy
from psyplot.utils import unique_everseen


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
        for arr in self.grouper.arrays:
            child = QTreeWidgetItem(0)
            self.addChild(child)
            # variable name
            child.setText(0, arr.name)
            # checkbox
            cb = QCheckBox()
            cb.setChecked(self.grouper.is_visible(arr))
            cb.stateChanged.connect(self.show_or_hide_func(arr.name))
            self.tree.setItemWidget(child, 1, cb)
            # mean
            child.setText(2, '%1.3f' % arr.mean().values)
            # min
            child.setText(3, '%1.3f' % arr.min().values)
            # max
            child.setText(4, '%1.3f' % arr.max().values)

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
    """A widget for managing the stratographic plots from the psy-strat package
    """

    #: The title of the widget
    title = 'Stratographic plots'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    @property
    def stratplotter_cls(self):
        """The :class:`psy_strat.plotters.StratPlotter` class if it's
        module has already been imported. Otherwise None."""
        if 'psy_strat.plotters' not in sys.modules:
            return None
        from psy_strat.plotters import StratPlotter
        return StratPlotter

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
            for group in unique_everseen(arr.attrs['group'] for arr in arrs):
                arrays = project(group=group)
                identifier = ds[group].identifier
                grouper_cls = strat_groupers[identifier]
                groupers.append(grouper_cls(arrays, use_weakref=True))
            title = 'Dataset %i' % num
            if fnames[num]:
                title += ': ' + fnames[num]
            self.add_tree(groupers, title)
        if self.hidden:
            self.hide_plugin()

    def add_tree(self, groupers, title=None):
        """Add a new QTreeWidget to the :attr:`tabs` widget"""
        tree = QTreeWidget(parent=self)
        tree.setColumnCount(5)
        tree.setHeaderLabels(['Name', 'Visible', 'mean', 'min', 'max'])
        ds = groupers[0].arrays[0].psy.base

        # fill the tree
        for grouper in groupers:
            top = GrouperItem(grouper, tree, 0)
            tree.addTopLevelItem(top)
            top.add_array_children()

        self.tabs.addTab(tree, title or 'Dataset %i' % ds.psy.num)
        tree.expandAll()
        for i in range(5):
            tree.resizeColumnToContents(i)
        self.show_plugin()
        self.groupers[ds.psy.num] = groupers
        self.trees[ds.psy.num] = tree
