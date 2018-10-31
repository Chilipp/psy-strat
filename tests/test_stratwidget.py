# -*- coding: utf-8 -*-
"""Test module for :mod:`psy_strat.stratwidget`

Requires psyplot-gui package to be installed"""
import gc
import os
import os.path as osp
import unittest
import test_stratplot as ts

from psyplot_gui.compat.qtcompat import QApplication, QTest, Qt
from psyplot_gui import rcParams


test_dir = osp.dirname(__file__)


def is_running_in_gui():
    from psyplot_gui.main import mainwindow
    return mainwindow is not None


def setup_rcparams():
    rcParams.defaultParams['console.start_channels'][0] = False
    rcParams.defaultParams['main.listen_to_port'][0] = False
    rcParams.defaultParams['help_explorer.render_docs_parallel'][0] = False
    rcParams.defaultParams['help_explorer.use_intersphinx'][0] = False
    rcParams.defaultParams['plugins.include'][0] = ['psy_strat.strat_widget']
    rcParams.defaultParams['plugins.exclude'][0] = 'all'
    rcParams.update_from_defaultParams()


running_in_gui = is_running_in_gui()


on_travis = os.environ.get('TRAVIS')


if running_in_gui:
    app = QApplication.instance()
else:
    setup_rcparams()
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)


class StratPlotsWidgetsTestMixin(object):
    """A base class for testing the strat_widget module

    At the initializzation of the TestCase, a new
    :class:`psyplot_gui.main.MainWindow` widget is created which is closed at
    the end of all the tests"""

    @classmethod
    def setUpClass(cls):
        import psyplot_gui.main as main
        if not running_in_gui:
            cls.window = main.MainWindow.run(show=False)
        else:
            cls.window = main.mainwindow

    def setUp(self):
        self.created_files = set()

    def tearDown(self):
        import matplotlib.pyplot as plt
        import psyplot.project as psy
        plt.close('all')
        psy.close('all')
        for f in self.created_files:
            if osp.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    @classmethod
    def tearDownClass(cls):
        if not running_in_gui:
            import psyplot_gui.main as main
            cls.window.close()
            rcParams.update_from_defaultParams()
            rcParams.disconnect()
            main._set_mainwindow(None)
            del cls.window

    # ------- Convenience methods ---------------------------------------------

    @property
    def current_tree(self):
        import psyplot.project as psy
        from psy_strat.strat_widget import get_stratplots_widgets
        num = list(psy.gcp().datasets)[0]
        stratplots = get_stratplots_widgets(self.window)
        tree = stratplots.trees.get(num)
        self.assertIsNotNone(tree, msg=stratplots.trees)
        return tree

    @property
    def current_groupers(self):
        import psyplot.project as psy
        from psy_strat.strat_widget import get_stratplots_widgets
        num = list(psy.gcp().datasets)[0]
        stratplots = get_stratplots_widgets(self.window)
        groupers = stratplots.groupers.get(num)
        self.assertIsNotNone(groupers, msg=stratplots.groupers)
        return groupers

    def test_stratplot(self):
        sp, groupers = super().test_stratplot()

        self.assertEqual(self.current_groupers, groupers)
        return sp, groupers

    def test_moving(self):
        """Test the movement of arrays"""
        from psy_strat.strat_widget import get_stratplots_widgets
        self.test_stratplot()
        tree = self.current_tree
        top = tree.topLevelItem(0)
        child = top.child(0)
        child.setSelected(True)
        w = get_stratplots_widgets(self.window)

        # test moving down
        w.move_selected_children(child, 2)
        self.assertIs(top.child(1), child)

        w.move_selected_children(child, 2)
        self.assertIs(top.child(2), child)

        # test moving up
        w.move_selected_children(child, 1)
        self.assertIs(top.child(1), child)
        w.move_selected_children(child, 1)
        self.assertIs(top.child(0), child)

        # test moving the end
        tree.clearSelection()
        nchilds = top.childCount()
        child = top.child(nchilds - 1)
        w.move_selected_children(child, 1)
        self.assertIs(top.child(nchilds - 2), child)
        w.move_selected_children(child, 2)
        self.assertIs(top.child(nchilds - 1), child)

    def test_project(self):
        import psyplot.project as psy
        from psy_strat.strat_widget import get_stratplots_widgets
        w = get_stratplots_widgets(self.window)
        sp = self.test_stratplot()[0]
        d = sp.save_project(ds_description={'ds'})
        psy.close('all')
        self.assertFalse(psy.gcp(True))
        self.assertFalse(w.trees)

        sp = sp.load_project(d)
        self.assertTrue(w.trees)
        self.assertEqual(list(w.trees), list(sp.datasets))


class WidgetsStratGroupTest(StratPlotsWidgetsTestMixin, ts.StratGroupTest):
    pass


class WidgetsStratPercentagesTest(StratPlotsWidgetsTestMixin,
                                  ts.StratPercentagesTest):
    pass


class WidgetsStratAllInOneTest(StratPlotsWidgetsTestMixin,
                               ts.StratAllInOneTest):
    pass


class WidgetsStackedGroupTest(StratPlotsWidgetsTestMixin,
                              ts.StackedGroupTest):
    pass


if __name__ == '__main__':
    unittest.main()
