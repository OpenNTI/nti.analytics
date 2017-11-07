#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.analytics.stats.interfaces import IActiveTimesStats
from nti.analytics.stats.interfaces import IActiveTimesStatsSource

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


@interface.implementer(IActiveTimesStatsSource)
class ActiveTimeSource(object):

    EVENT_SOURCES = (get_video_views,
                     get_resource_views,)

    def __init__(self, user=None, course=None):
        self.user = user
        self.course = course

    def active_times_for_window(self, start, end):
        stats = ActiveTimeStats()
        for source in self.EVENT_SOURCES:
            events = source(user=self.user,
                            course=self.course,
                            timestamp=start,
                            max_timestamp=end)
            for event in events:
                stats.process_event(event)
        return stats
