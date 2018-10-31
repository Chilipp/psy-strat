"""Test module for :mod:`psy_strat.stratplot`"""

import unittest
import numpy as np
import pandas as pd
from psy_strat.stratplot import stratplot


#: Test dataframe with six columns. c, d and f are percentages that sum up to
#: 100
test_df = pd.DataFrame(np.transpose(
                            [[1, 1, 1],
                             [1, 2, 1],
                             [2, 2, 3],
                             [33, 24, 28],
                             [50, 34, 69],
                             [17, 42, 3]]),
                       columns=list('abcdef'))


class StratGroupTest(unittest.TestCase):
    """Test the handling of :class:`psy_strat.stratplot.StratGroup`"""

    def tearDown(self):
        import psyplot.project as psy
        psy.close('all')

    def test_stratplot(self, *args, **kwargs):
        sp, groupers = stratplot(test_df)
        grouper = groupers[0]
        self.assertEqual(list(map(lambda ax: ax.get_title('left'),
                                  grouper.axes)),
                         list(test_df.columns))
        self.assertEqual(len(grouper.plotter_arrays), len(test_df.columns))
        for (col, vals), ax in zip(test_df.items(), grouper.axes):
            self.assertEqual(list(ax.lines[0].get_xdata()), list(vals),
                             msg='Wrong data for column %s' % col)
        for col, ax0, ax1 in zip(test_df.columns, grouper.axes,
                                 grouper.axes[1:]):
            self.assertEqual(
                ax0.get_position().x1, ax1.get_position().x0,
                msg="Positions of col %s don't line up!\nax0: %s\nax1: %s" % (
                    col, ax0.get_position(), ax1.get_position()))

        return sp, groupers


class StratPercentagesTest(unittest.TestCase):

    def tearDown(self):
        import psyplot.project as psy
        psy.close('all')

    def test_stratplot(self):
        sp, groupers = stratplot(
            test_df, widths={'1': 0.5, '2': 0.5},
            group_func=lambda g: '1' if g <= 'c' else '2', percentages=['2'])
        grouper = groupers[1]
        self.assertEqual(len(grouper.plotter_arrays), 3)
        for (col, vals), da in zip(test_df.iloc[:, 3:].items(),
                                   grouper.arrays):
            self.assertEqual(list(da.values), list(vals),
                             msg='Wrong data for column %s' % col)
        return sp, groupers


class StratAllInOneTest(unittest.TestCase):

    def tearDown(self):
        import psyplot.project as psy
        psy.close('all')

    def test_stratplot(self):
        sp, groupers = stratplot(
            test_df, widths={'1': 0.5, '2': 0.5},
            group_func=lambda g: '1' if g <= 'c' else '2', all_in_one=['2'])
        grouper = groupers[1]
        self.assertEqual(len(grouper.plotter_arrays), 1)
        for (col, vals), da in zip(test_df.iloc[:, 3:].items(),
                                   grouper.arrays):
            self.assertEqual(list(da.values), list(vals),
                             msg='Wrong data for column %s' % col)
        return sp, groupers


class StackedGroupTest(unittest.TestCase):

    def tearDown(self):
        import psyplot.project as psy
        psy.close('all')

    def test_stratplot(self):
        sp, groupers = stratplot(
            test_df, widths={'1': 0.5, '2': 0.5},
            group_func=lambda g: '1' if g <= 'c' else '2', stacked=['2'])
        grouper = groupers[1]
        self.assertEqual(len(grouper.plotter_arrays), 1)
        for (col, vals), da in zip(test_df.iloc[:, 3:].items(),
                                   grouper.arrays):
            self.assertEqual(list(da.values), list(vals),
                             msg='Wrong data for column %s' % col)
        return sp, groupers

    def test_summed(self):
        """Test the summed version"""
        sp, groupers = stratplot(
            test_df, widths={'1': 0.3, '2': 0.5, 'Summed': 0.2},
            group_func=lambda g: '1' if g <= 'c' else '2',
            summed=True)
        summed = [test_df.iloc[:, :3].sum(axis=1).values,
                  test_df.iloc[:, 3:].sum(axis=1).values]
        grouper = groupers[-1]
        self.assertEqual(len(grouper.plotter_arrays), 1)
        for i, (vals, da) in enumerate(zip(summed, grouper.arrays)):
            self.assertEqual(list(da.values), list(vals),
                             msg='Wrong data for column %s' % i)
        return sp, groupers


if __name__ == '__main__':
    unittest.main()
