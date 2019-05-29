#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict

from gevent import sleep

from zope import interface

from nti.analytics.lti import get_active_users_with_lti_asset_launches
from nti.analytics.lti import get_lti_asset_launches

from nti.analytics.assessments import get_active_users_with_assignments_taken
from nti.analytics.assessments import get_assignment_taken_views

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

from nti.analytics.scorm import get_active_users_with_scorm_package_launches
from nti.analytics.scorm import get_scorm_package_launches

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
                 get_resource_views,
                 get_scorm_package_launches,
                 get_lti_asset_launches,
                 get_assignment_taken_views)

_DEFAULT_YIELD_PER = 1000


def _activity_source(**kwargs):
    yield_to_hub_per = kwargs.get('yield_per', None) or _DEFAULT_YIELD_PER
    for source in EVENT_SOURCES:
        count_provided = 0
        for event in source(**kwargs):
            count_provided += 1
            yield event
            if count_provided >= yield_to_hub_per:
                count_provided = 0
                sleep() # Yield to the gevent hub


@interface.implementer(IActivitySource)
class ActivitySource(object):

    def __init__(self, user=None, root_context=None):
        self.user = user
        self.root_context = root_context

    def activity(self, **kwargs):
        kwargs['user'] = self.user
        kwargs['root_context'] = self.root_context
        if 'yield_per' not in kwargs:
            kwargs['yield_per'] = _DEFAULT_YIELD_PER
        events = _activity_source(**kwargs)

        order_by = kwargs.get('order_by', None)

        if order_by:
            events = sorted(events,
                            key=lambda a: getattr(a, order_by),
                            reverse=True)

        limit = kwargs.get('limit', None)
        return events[:limit] if limit else events


def _root_context_activity_source(root_context):
    return ActivitySource(root_context=root_context)


def _active_time_for_user(user):
    return ActiveTimeSource(user=user)


def _active_time_for_root_context(root_context):
    return ActiveTimeSource(root_context=root_context)


def _active_time_for_enrollment(user, course):
    return ActiveTimeSource(user=user,
                            root_context=course)


def _active_time(root=None):
    return ActiveTimeSource()


@interface.implementer(IActiveTimesStatsSource)
class ActiveTimeSource(object):

    def __init__(self, user=None, root_context=None):
        self.user = user
        self.root_context = root_context

    def active_times_for_window(self, start, end):
        stats = ActiveTimeStats()
        activity_source = ActivitySource(user=self.user,
                                         root_context=self.root_context)
        for event in activity_source.activity(timestamp=start,
                                              max_timestamp=end):
            stats.process_event(event)
        return stats
    stats_for_window = active_times_for_window


def _daily_activity_for_user(user):
    return DailyActivitySource(user=user)


def _daily_activity_for_root_context(root_context):
    return DailyActivitySource(root_context=root_context)


def _daily_activity_for_enrollment(user, course):
    return DailyActivitySource(user=user,
                               root_context=course)


def _daily_activity(root=None):
    return DailyActivitySource()


@interface.implementer(IDailyActivityStatsSource)
class DailyActivitySource(object):

    def __init__(self, user=None, root_context=None):
        self.user = user
        self.root_context = root_context

    def stats_for_window(self, start, end):
        dates = defaultdict(lambda: 0)
        activity_source = ActivitySource(user=self.user,
                                         root_context=self.root_context)
        for event in activity_source.activity(timestamp=start,
                                              max_timestamp=end):
            date = event.timestamp.date()
            dates[date] += 1
        return LocatedExternalDict({k: CountStats(Count=v)
                                    for k, v in dates.items()})


BY_USER_EVENTS = (get_active_users_with_video_views,
                  get_active_users_with_resource_views,
                  get_active_users_with_scorm_package_launches,
                  get_active_users_with_lti_asset_launches,
                  get_active_users_with_assignments_taken)


@interface.implementer(IActiveUsersSource)
class ActiveUsersSource(object):

    def __init__(self, root_context=None):
        self.root_context = root_context

    def users(self, **kwargs):
        aggregate = defaultdict(lambda: 0)
        for source in BY_USER_EVENTS:
            for user, count in source(root_context=self.root_context, **kwargs):
                aggregate[user] += count
        return sorted(aggregate, key=aggregate.get, reverse=True)

