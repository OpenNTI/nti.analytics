#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict

from zope import interface

from nti.analytics.stats.interfaces import IActiveTimesStats
from nti.analytics.stats.interfaces import IActiveTimesStatsSource
from nti.analytics.stats.interfaces import IDailyActivityStatsSource

from nti.analytics.stats.model import CountStats

from nti.analytics.resource_views import get_resource_views
from nti.analytics.resource_views import get_video_views

logger = __import__('logging').getLogger(__name__)


class _CountStatsWrapping(object):

    def __init__(self, stats):
        self.stats = stats

    def __getitem__(self, key):
        count = self.stats.get(key, 0)
        return CountStats(Count=count)


@interface.implementer(IActiveTimesStats)
class ActiveTimeStats(object):

    def __init__(self):
        self.counts = {}

    def process_event(self, event):
        day = event.timestamp.weekday()
        hour = event.timestamp.hour

        try:
            day_counts = self.counts[day]
        except KeyError:
            day_counts = {}
            self.counts[day] = day_counts

        day_counts[hour] = day_counts.get(hour, 0) + 1

    def __getitem__(self, key):
        day_counts = self.counts.get(key, {})
        return _CountStatsWrapping(day_counts)

EVENT_SOURCES = (get_video_views,
                 get_resource_views,)

def _activity_source(**kwargs):
    for source in EVENT_SOURCES:
        for event in source(**kwargs):
            yield event


@interface.implementer(IActiveTimesStatsSource)
class ActiveTimeSource(object):

    def __init__(self, user=None, course=None):
        self.user = user
        self.course = course

    def active_times_for_window(self, start, end):
        stats = ActiveTimeStats()
        for event in _activity_source(user=self.user,
                                      course=self.course,
                                      timestamp=start,
                                      max_timestamp=end):
            stats.process_event(event)
        return stats
    stats_for_window = active_times_for_window

@interface.implementer(IDailyActivityStatsSource)
class DailyActivitySource(object):

    def __init__(self, user=None, course=None):
        self.user = user
        self.course = course

    def stats_for_window(self, start, end):
        dates = defaultdict(lambda: 0)
        for event in _activity_source(user=self.user,
                                      course=self.course,
                                      timestamp=start,
                                      max_timestamp=end):
            date = event.timestamp.date()
            dates[date] += 1
        return {k: CountStats(Count=v) for k,v in dates.items()}


