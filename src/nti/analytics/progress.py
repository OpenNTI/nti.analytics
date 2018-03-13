#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime

from zope import interface

from nti.analytics.interfaces import IVideoProgress

from nti.analytics.boards import get_topic_views

from nti.contenttypes.completion.progress import Progress

from nti.externalization.representation import WithRepr

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

logger = __import__('logging').getLogger(__name__)


@WithRepr
@EqHash('NTIID', 'AbsoluteProgress', 'MaxPossibleProgress',
        'HasProgress', 'LastModified', 'MostRecentEndTime')
@interface.implementer(IVideoProgress)
class VideoProgress(Progress):

    createDirectFieldProperties(IVideoProgress)

    __external_can_create__ = False

    # Re-use the original class for BWC.
    __external_class_name__ = "Progress"
    mime_type = mimeType = 'application/vnd.nextthought.videoprogress'


def _get_last_mod(last_mod):
    """
    Gets the last_mod DateTime object.
    """
    try:
        last_mod = datetime.utcfromtimestamp(last_mod)
    except TypeError:
        # tests
        last_mod = last_mod
    return last_mod


def get_progress_for_resource_container(resource_ntiid, resource_view_dict):
    """
    For a page container, use the children progress to determine
    aggregate progress for the container, which should typically return a
    num_of_pages_viewed/num_of_pages fraction.
    """
    # Get progress for each child
    children_progress = (get_progress_for_resource_views( child_ntiid, child_views )
                        for child_ntiid, child_views in resource_view_dict.items())

    children_progress = [x for x in children_progress if x]

    progress = None
    if children_progress:
        # Each page with *any* progress is viewed
        viewed_pages = sum(1 for x in children_progress if x and x.HasProgress)
        num_pages = len(resource_view_dict)
        last_mod = max(x.LastModified for x in children_progress if x)
        progress = Progress(NTIID=resource_ntiid,
                            AbsoluteProgress=viewed_pages,
                            MaxPossibleProgress=num_pages,
                            LastModified=last_mod,
                            HasProgress=bool(viewed_pages))
    return progress


def get_progress_for_resource_views(resource_ntiid, resource_views):
    """
    For a set of events for a given ntiid, looking at a resource
    constitutes progress.
    """
    progress = None
    if resource_views:
        resource_views = tuple(resource_views)
        # Grabbing the first timestamp we see for last mod,
        # because once they have progress, state will not change.
        last_mod = next(ts for ts in
                        (x.timestamp for x in resource_views)
                        if ts is not None)
        last_mod = _get_last_mod(last_mod)
        total_time = sum(x.time_length for x in resource_views
						if x.time_length is not None)
        progress = Progress(NTIID=resource_ntiid,
                            AbsoluteProgress=total_time,
                            MaxPossibleProgress=None,
                            LastModified=last_mod,
                            HasProgress=True)
    return progress


def get_progress_for_video_views(resource_ntiid, video_events):
    """
    For a set of events for a given ntiid, looking at a resource
    constitutes progress.
    """
    progress = None
    # Note: currently, 'None' time_lengths (placeholders for event starts)
    # are considered progress.

    if video_events:
        video_events = tuple(video_events)
        # XXX: Perhaps we want the most recent max time (max time may be null)
        sorted_events = sorted(video_events, key=lambda x: x.timestamp, reverse=True)
        most_recent_event = sorted_events[0]
        max_time = max(x.MaxDuration for x in video_events)
        last_mod = most_recent_event.timestamp
        last_end_time = most_recent_event.VideoEndTime
        last_mod = _get_last_mod(last_mod)
        total_time = sum(x.time_length for x in video_events if x.time_length is not None)
        progress = VideoProgress(NTIID=resource_ntiid,
                                 AbsoluteProgress=total_time,
                                 MaxPossibleProgress=max_time,
                                 LastModified=last_mod,
                                 HasProgress=True,
                                 MostRecentEndTime=last_end_time)
    return progress


def _get_last_mod_progress(values, id_val):
    """
    For a collection of items, gather progress based on last modified
    timestamp.
    """
    progress = None
    if values:
        last_mod = max(x.timestamp for x in values)
        last_mod = _get_last_mod(last_mod)
        progress = Progress(NTIID=id_val,
                            AbsoluteProgress=None,
                            MaxPossibleProgress=None,
                            LastModified=last_mod,
                            HasProgress=True)
    return progress


def get_topic_progress( user, topic ):
    """
    Returns all assessment progress for a given user and topic.
    """
    topic_views = get_topic_views( user, topic )
    result = _get_last_mod_progress( topic_views, topic.NTIID )
    return result
