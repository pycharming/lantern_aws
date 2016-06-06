#!/usr/bin/env python

from datetime import datetime, timedelta
import unittest

import stats


def sample(**kwargs):
    return stats.sample(**{name: kwargs.get(name, 77.77)
                           for name in stats.name2def})

class TestReduceStats(unittest.TestCase):

    def setUp(self):
        now = datetime.utcnow()
        self.sample_times = [now - timedelta(minutes=m)
                             for m in xrange(10)]
        self.sample_times.reverse()

    def deep_aoe(self, actual, expected):
        """
        A version of assertAlmostEqual that looks into data structures.

        Support for specific types is only added in a per need basis.
        """
        if isinstance(expected, dict):
            self.assertIsInstance(actual, dict)
            self.assertEqual(expected.keys(), actual.keys())
            for k in expected.keys():
                self.deep_aoe(expected[k], actual[k])
        elif isinstance(expected, float):
            self.assertAlmostEqual(expected, actual)
        else:
            self.assertEqual(expected, actual)

    def test_no_samples(self):
        self.assertEqual(stats.reduce_stats(['load_avg', 'disk_tx'], []),
                         {'actual_start_time': None,
                          'values': {'load_avg': None, 'disk_tx': None}})
    def test_single_sample(self):
        self.assertEqual(stats.reduce_stats(['load_avg', 'disk_tx'],
                                            [sample(time=self.sample_times[0], load_avg=1.2, disk_tx=123456)]),
                         {'actual_start_time': self.sample_times[0],
                          'values': {'load_avg': 1.2, 'disk_tx': 0}})

    def test_two_equal_samples(self):
        self.deep_aoe(stats.reduce_stats(['load_avg', 'disk_tx'],
                                         [sample(time=self.sample_times[0], load_avg=1.2, disk_tx=123456),
                                          sample(time=self.sample_times[1], load_avg=1.2, disk_tx=123456)]),
                      {'actual_start_time': self.sample_times[0],
                       'values': {'load_avg': 1.2, 'disk_tx': 0}})

    def test_two_increasing_samples(self):
        self.deep_aoe(stats.reduce_stats(['load_avg', 'disk_tx'],
                                         [sample(time=self.sample_times[0], load_avg=1.2, disk_tx=123456),
                                          sample(time=self.sample_times[1], load_avg=1.4, disk_tx=123556)]),
                      {'actual_start_time': self.sample_times[0],
                       'values': {'load_avg': 1.3, 'disk_tx': 100}})

    def test_three_monotonically_increasing_samples(self):
        self.deep_aoe(stats.reduce_stats(['load_avg', 'disk_tx'],
                                         [sample(time=self.sample_times[0], load_avg=1.2, disk_tx=123456),
                                          sample(time=self.sample_times[1], load_avg=1.3, disk_tx=123506),
                                          sample(time=self.sample_times[2], load_avg=1.4, disk_tx=123556)]),
                      {'actual_start_time': self.sample_times[0],
                       'values': {'load_avg': 1.3, 'disk_tx': 100}})

    def test_three_non_monotonically_increasing_samples(self):
        """
        For dimensions of accum_type==delta_type, a value that is lower than
        the previous one will be taken as evidence that there has been a
        reboot.

        In this case, we count 50 disk_tx before the reboot and 100 after. This
        is the only case where the absolute value of a delta_type sample
        matters. In all the others, we only care about its difference with the
        previous sample.
        """
        self.deep_aoe(stats.reduce_stats(['load_avg', 'disk_tx'],
                                         [sample(time=self.sample_times[0], load_avg=1.2, disk_tx=123456),
                                          sample(time=self.sample_times[1], load_avg=1.3, disk_tx=123506),
                                          sample(time=self.sample_times[2], load_avg=1.25, disk_tx=100)]),
                      {'actual_start_time': self.sample_times[0],
                       'values': {'load_avg': 1.25, 'disk_tx': 150}})

if __name__ == '__main__':
    unittest.main()
