#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property

import unittest

from zope import component

from nti.analytics.tests import NTIAnalyticsTestCase

from datetime import datetime
from datetime import timedelta

from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.users import User

from nti.analytics.stats.activity import ActiveTimeStats
from nti.analytics.stats.activity import DailyActivitySource

from nti.analytics.stats.interfaces import IActiveTimesStatsSource
from nti.analytics.stats.interfaces import IDailyActivityStatsSource


class FakeEvent(object):
    timestamp = None

    def __init__(self, timestamp=None):
        self.timestamp = timestamp


class TestActiveTimeStats(unittest.TestCase):

    def test_time_stats(self):
        stats = ActiveTimeStats()

        # python day indexes start 0=mon, 6=sun
        timestamps = {
            0: {
                11: 3,
                2: 6
            },
            1: {
                1: 3,
                4: 6
            },
            2: {
                7: 3,
                3: 6
            },
            3: {
                23: 3,
                1: 6
            },
            4: {
                0: 3,
                2: 6
            },
            5: {
                11: 3,
                2: 6
            },
            6: {
                13: 3,
                7: 6
            }
        }

        now = datetime.now()

        for day, hours in timestamps.items():
            for hour, count in hours.items():
                timestamp = now - timedelta(days=now.weekday())
                timestamp = timestamp + timedelta(days=day)
                timestamp = timestamp.replace(hour=hour)
                for _ in range(count):
                    event = FakeEvent()
                    event.timestamp = timestamp
                    stats.process_event(event)

        for day, hours in timestamps.items():
            for hour, count in hours.items():
                assert_that(stats[day][hour].Count,
                            is_(count),
                            'day {} hour {}'.format(day, hour))

        assert_that(stats[5][1].Count, is_(0))

class TestActiveTimeStatsAdapters(NTIAnalyticsTestCase):

    def setUp(self):
        super(TestActiveTimeStatsAdapters, self).setUp()
        self.user = User('aspecificuser')
        self.course = CourseInstance()
        self.start = datetime.now()
        self.end = datetime.now()

    @fudge.patch('nti.analytics.stats.activity._activity_source')
    def test_user_scoped(self, mock_activity_source):
        mock_activity_source.is_callable().with_matching_args(user=self.user,
                                                     course=None,
                                                     timestamp=self.start,
                                                     max_timestamp=self.end)
        mock_activity_source.returns([])

        source = IActiveTimesStatsSource(self.user)
        source.stats_for_window(self.start, self.end)

    @fudge.patch('nti.analytics.stats.activity._activity_source')
    def test_course_scoped(self, mock_activity_source):
        mock_activity_source.is_callable().with_matching_args(user=None,
                                                     course=self.course,
                                                     timestamp=self.start,
                                                     max_timestamp=self.end)
        mock_activity_source.returns([])

        source = IActiveTimesStatsSource(self.course)
        source.stats_for_window(self.start, self.end)

    @fudge.patch('nti.analytics.stats.activity._activity_source')
    def test_enrollment_scoped(self, mock_activity_source):
        mock_activity_source.is_callable().with_matching_args(user=self.user,
                                                     course=self.course,
                                                     timestamp=self.start,
                                                     max_timestamp=self.end)
        mock_activity_source.returns([])

        source = component.getMultiAdapter((self.user, self.course), IActiveTimesStatsSource)
        source.stats_for_window(self.start, self.end)


class TestDailyActivitySource(unittest.TestCase):

    TIMES = ['2010-01-01 12:03',
             '2010-01-01 14:03',
             '2010-01-02 12:03',
             '2010-03-01 15:03', ]

    @fudge.patch('nti.analytics.stats.activity._activity_source')
    def test_daily_activity_summary(self, mock_activity_source):

        mock_activity_source.is_callable()
        mock_activity_source.returns([
            FakeEvent(datetime.strptime(s, "%Y-%m-%d %H:%M")) for s in self.TIMES
        ])

        source = DailyActivitySource()
        result = source.stats_for_window(None, None)
        assert_that(result,
                    has_entries(datetime(2010, 1, 1).date(), has_property('Count', 2),
                                datetime(2010, 1, 2).date(), has_property('Count', 1),
                                datetime(2010, 3, 1).date(), has_property('Count', 1)))

class TestDailyActivitySourceAdapters(NTIAnalyticsTestCase):

    def setUp(self):
        super(TestDailyActivitySourceAdapters, self).setUp()
        self.user = User('aspecificuser')
        self.course = CourseInstance()
        self.start = datetime.now()
        self.end = datetime.now()

    @fudge.patch('nti.analytics.stats.activity._activity_source')
    def test_user_scoped(self, mock_activity_source):
        mock_activity_source.is_callable().with_matching_args(user=self.user,
                                                     course=None,
                                                     timestamp=self.start,
                                                     max_timestamp=self.end)
        mock_activity_source.returns([])

        source = IDailyActivityStatsSource(self.user)
        source.stats_for_window(self.start, self.end)

    @fudge.patch('nti.analytics.stats.activity._activity_source')
    def test_course_scoped(self, mock_activity_source):
        mock_activity_source.is_callable().with_matching_args(user=None,
                                                     course=self.course,
                                                     timestamp=self.start,
                                                     max_timestamp=self.end)
        mock_activity_source.returns([])

        source = IDailyActivityStatsSource(self.course)
        source.stats_for_window(self.start, self.end)

    @fudge.patch('nti.analytics.stats.activity._activity_source')
    def test_enrollment_scoped(self, mock_activity_source):
        mock_activity_source.is_callable().with_matching_args(user=self.user,
                                                     course=self.course,
                                                     timestamp=self.start,
                                                     max_timestamp=self.end)
        mock_activity_source.returns([])

        source = component.getMultiAdapter((self.user, self.course), IDailyActivityStatsSource)
        source.stats_for_window(self.start, self.end)
