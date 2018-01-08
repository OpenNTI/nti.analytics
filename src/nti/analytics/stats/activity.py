#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict

from zope import component
from zope import interface

from nti.analytics.stats.interfaces import IActivitySource
from nti.analytics.stats.interfaces import IActiveTimesStats
from nti.analytics.stats.interfaces import IActiveTimesStatsSource
from nti.analytics.stats.interfaces import IActiveUsersSource
from nti.analytics.stats.interfaces import IDailyActivityStatsSource

from nti.analytics.stats.model import CountStats

from nti.analytics.resource_views import get_video_views
from nti.analytics.resource_views import get_resource_views
from nti.analytics.resource_views import get_active_users_with_resource_views
from nti.analytics.resource_views import get_active_users_with_video_views

from nti.dataserver.interfaces import IUser

from nti.externalization.interfaces import LocatedExternalDict

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

_DEFAULT_YIELD_PER = 1000

def _activity_source(**kwargs):
    for source in EVENT_SOURCES:
        for event in source(**kwargs):
            yield event

@interface.implementer(IActivitySource)
class ActivitySource(object):

    def __init__(self, user=None, course=None):
        self.user = user
        self.course = course

    def activity(self, **kwargs):
        kwargs['user'] = self.user
        kwargs['course'] = self.course
        if 'yield_per' not in kwargs:
            kwargs['yield_per'] = _DEFAULT_YIELD_PER
        events = _activity_source(**kwargs)

        order_by = kwargs.get('order_by', None)

        if order_by:
            events = sorted(events,
                            key=lambda a: getattr(a, order_by),
                            reverse=True)

        limit = kwargs.get('limit', None)
        return events[0:limit] if limit else events

def _course_activity_source(course):
    return ActivitySource(course=course)

def _active_time_for_user(user):
    return ActiveTimeSource(user=user)

def _active_time_for_course(course):
    return ActiveTimeSource(course=course)

def _active_time_for_enrollment(user, course):
    return ActiveTimeSource(user=user,
                            course=course)

def _active_time(root=None):
    return ActiveTimeSource()

@interface.implementer(IActiveTimesStatsSource)
class ActiveTimeSource(object):

    def __init__(self, user=None, course=None):
        self.user = user
        self.course = course

    def active_times_for_window(self, start, end):
        stats = ActiveTimeStats()
        activity_source = ActivitySource(user=self.user, course=self.course)
        for event in activity_source.activity(timestamp=start, max_timestamp=end):
            stats.process_event(event)
        return stats
    stats_for_window = active_times_for_window

def _daily_activity_for_user(user):
    return DailyActivitySource(user=user)

def _daily_activity_for_course(course):
    return DailyActivitySource(course=course)

def _daily_activity_for_enrollment(user, course):
    return DailyActivitySource(user=user,
                               course=course)

def _daily_activity(root=None):
    return DailyActivitySource()


@interface.implementer(IDailyActivityStatsSource)
class DailyActivitySource(object):

    def __init__(self, user=None, course=None):
        self.user = user
        self.course = course

    def stats_for_window(self, start, end):
        dates = defaultdict(lambda: 0)
        activity_source = ActivitySource(user=self.user, course=self.course)
        for event in activity_source.activity(timestamp=start, max_timestamp=end):
            date = event.timestamp.date()
            dates[date] += 1
        return LocatedExternalDict({k: CountStats(Count=v) for k, v in dates.items()})

@interface.implementer(IActiveUsersSource)
class ActiveUsersSource(object):

    def __init__(self, course=None):
        self.course = course

    def users(self, **kwargs):
        aggregate = defaultdict(lambda: 0)
        for source in (get_active_users_with_video_views, get_active_users_with_resource_views):
            for user, count in source(course=self.course, **kwargs):
                aggregate[user] += count
        return sorted(aggregate, key=aggregate.get, reverse=True)



