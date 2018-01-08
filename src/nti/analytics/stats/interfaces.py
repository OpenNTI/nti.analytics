#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.schema.field import Float
from nti.schema.field import Number


class IStats(interface.Interface):
    """
    A stats object.
    """


class ICountStats(IStats):
    """
    A container for holding the count of events.
    """

    Count = Number(title=u"Count", required=True)


class IPostMixin(ICountStats):
    TopLevelCount = Number(title=u"The number of top level posts.",
                           required=True)

    ReplyCount = Number(title=u"The number of reply posts.",
                        required=True)

    DistinctPostsLiked = Number(title=u"The number of distinct posts liked.",
                                required=True)

    DistinctPostsFavorited = Number(title=u"The number of distinct posts favorited.",
                                    required=True)

    TotalLikes = Number(title=u"The total number of posts liked.",
                        required=True)

    TotalFavorites = Number(title=u"The total number of posts favorited.",
                            required=True)

    RecursiveChildrenCount = Number(title=u"The total number of direct or indirect children of this post.",
                                    required=True)
    StandardDeviationLength = Float(title=u"Standard deviation body length",
                                    required=False)

    AverageLength = Float(title=u"Average body length", required=True)

    ContainsWhiteboardCount = Number(title=u"The total amount of time spent.",
                                     required=True)


class INoteStats(IPostMixin):
    """
    A container for holding various note stats.
    """


class ICommentStats(IPostMixin):
    """
    A container for holding various comment stats.
    """


class IThoughtCommentStats(IPostMixin):
    """
    A container for holding various comment stats.
    """


class ITimeStats(ICountStats):
    """
    A container for holding various time stats.
    """
    AggregateTime = Number(title=u"The total amount of time spent.",
                           required=True)

    StandardDeviationDuration = Float(title=u"Standard deviation duration",
                                      required=False)

    AverageDuration = Float(title=u"Average duration", required=True)


class IUniqueStatsMixin(ICountStats):
    """
    Establishes uniqueness counts.
    """
    UniqueCount = Number(title=u"Unique self assessment count", required=True)


class ISelfAssessmentStats(IUniqueStatsMixin):
    """
    A container for holding self-assessment stats.
    """


class IAssignmentStats(IUniqueStatsMixin):
    """
    A container for holding assignment stats.
    """
    AssignmentLateCount = Number(title=u"Unique self assessment count",
                                 required=True)

    TimedAssignmentCount = Number(title=u"Unique assignment count",
                                  required=True)

    TimedAssignmentLateCount = Number(title=u"Late assignment timed count",
                                      required=True)


class IAnalyticsStatsSource(interface.Interface):
    """
    A utility to provide stats.
    """


class IActiveSessionStats(ICountStats):
    """
    Information about sessions that appear to be active.
    """


class IActiveSessionStatsSource(IAnalyticsStatsSource):
    """
    A utility for returning IActiveSessionStats object
    """

    def __call__():
        """
        A callable that returns an IActiveSessionStats object
        """


class IBucketedStatsSource(IAnalyticsStatsSource):
    """
    Something that sources stats or stat sources by bucket.
    """

    def __getitem__(bucket):
        """
        Return the stats object or stat source objects for the bucket
        """


class IActiveTimesStats(IBucketedStatsSource):
    """
    An IBucketedStatsSource keyed by day index that returns
    an IBucketedStatsSource keyed by hour
    """


class IWindowedStatsSource(IAnalyticsStatsSource):
    """
    Something that can provide stats for a given window of time
    """

    def stats_for_window(start, end):
        """
        Provides stats for the given time window.
        """


class IActiveTimesStatsSource(IWindowedStatsSource):

    def active_times_for_window(start, end):
        """
        Returns an IActiveTimesStats object for the given
        [start, end) time window
        """


class IDailyActivityStatsSource(IWindowedStatsSource):
    """
    A windowed stats source that returns a dictionary
    mapping date objects and ICountStats for activity
    on days in the window
    """

class IActivitySource(interface.Interface):

    def activity(**kwargs):
        """
        Returns an iterator of IAnalyticsEvent objects that represent
        activity.  In general no guarentees are made about the order
        or number of items the iterator returns although certain implementations
        may support those contructs by the use of kwargs.
        """


class IActiveUsersSource(interface.Interface):
    """
    Something that can yield users who have been active on the site.
    """

    def users(**kwargs):
        """
        An iterator yielding tuple of (IUser, ICountStats) objects that represent active users.
        In general no guarentees are made about the order
        or number of items the iterator returns although certain implementations
        may support those contructs by the use of kwargs.
        """
