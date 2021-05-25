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

from nti.analytics.database import get_analytics_db
from nti.analytics.database.resources import get_resource_record

from nti.analytics.interfaces import IVideoProgress

from nti.analytics.resource_views import get_watched_segments_for_ntiid
from nti.analytics.resource_views import get_video_views_for_ntiid
from nti.analytics.resource_views import get_user_video_views

from nti.contenttypes.completion.progress import Progress

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.schema.eqhash import EqHash

logger = __import__('logging').getLogger(__name__)


@EqHash('NTIID', 'AbsoluteProgress', 'MaxPossibleProgress',
        'HasProgress', 'LastModified', 'MostRecentEndTime')
@interface.implementer(IVideoProgress)
class VideoProgress(Progress):

    __external_can_create__ = False

    # Re-use the original class for BWC.
    __external_class_name__ = "Progress"
    mime_type = mimeType = 'application/vnd.nextthought.videoprogress'

    def __init__(self, MostRecentEndTime=None, *args, **kwargs):
        super(VideoProgress, self).__init__(*args, **kwargs)
        self.MostRecentEndTime = MostRecentEndTime


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


def get_video_progress_for_course(user, course):
    """
    For a given user/course, return a collection of progress for
    all videos we have on record.

    This is very expensive, and now it's expensive and wasteful. We
    find all the events for a given user and course to determine the
    set of videos a user has progress on. In the past we at least used
    those results to compute progress but now we throw it all away and
    go back to the db with a more complex query.
    """
    resource_views = get_user_video_views(user, course)
    view_dict = {}

    # TODO find the videos we care about in a cheaper way.
    for resource_view in resource_views:
        view_dict.setdefault( resource_view.ResourceId, [] ).append( resource_view )

    result = []
    for ntiid, events in view_dict.items():
        video = find_object_with_ntiid(ntiid)
        progress = get_progress_for_video_views(ntiid, video, user, course)
        result.append(progress)
    return result


def get_progress_for_resource_container(resource_ntiid, resource_view_dict, item, user, course):
    """
    For a page container, use the children progress to determine
    aggregate progress for the container, which should typically return a
    num_of_pages_viewed/num_of_pages fraction.
    """
    # Get progress for each child
    children_progress = (get_progress_for_resource_views(child_ntiid,
                                                         child_views,
                                                         item,
                                                         user,
                                                         course)
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
                            Item=item,
                            User=user,
                            CompletionContext=course,
                            HasProgress=bool(viewed_pages))
    return progress


def get_progress_for_resource_views(resource_ntiid, resource_views, item, user, course):
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
                            Item=item,
                            User=user,
                            CompletionContext=course,
                            HasProgress=True)
    return progress

def _compute_watched_seconds(segments):
    """
    Given a list of tuples whose first two elements are the inclusive
    start and end time (in seconds) *ordered by start*, compute the
    number of unique seconds in the video that have been watched.

    There are several ways to go about this. A naive implementation
    would turn each segment into ranges, place those in a set and then
    get the length. That's very slow (216ms for a one hour video with
    1000 unique segments), in fact any use of range (or xrange) ends
    up quite slow. Another approach is given the video length (or
    really) max end point, you can iterate from start to the end point
    counting the seconds that exist in each segment. This is better
    but still slow (3.8ms for the same test case). Instead if we
    reduce the segments to a set of non overlapping (but equivalent)
    segments we can them simply sum the seconds covered by each
    segment. This is the fastest approach given the same inputs (748 us).
    """
    # Special case the common case of no data
    if not segments:
        return 0

    # Another special case is when we have a single segment.
    # This is easy to compute from the segment because there are
    # no overlapping regions
    if len(segments) == 1:
        return segments[0][1] - segments[0][0] + 1 # Both ends of the range are inclusive

    stack = []
    for segment in segments:
        top = stack[-1] if stack else None
        if top is None:
            stack.append(segment)
            continue
        overlaps = segment[0] <= top[1] and top[0] <= segment[1]
        if not overlaps:
            stack.append(segment)
        elif segment[1] > top[1]:
            stack[-1] = (top[0], segment[1])
    return sum(x[1]-x[0]+1 for x in stack)

def get_progress_for_video_views(resource_ntiid, item, user, course):
    """
    For a set of events for a given ntiid, looking at a resource
    constitutes progress. If we have no progress this function returns
    None, not an empty progress object
    """
    progress = None
    # Note: currently, 'None' time_lengths (placeholders for event starts)
    # are considered progress.

    db = get_analytics_db()
    video = get_resource_record(db, resource_ntiid)
    if not video:
        return None
    
    # We need the most recent watch event to get the MostRecentEndTime
    # lack of this also means that we have no segments and can short circuit
    most_recent_watch =  get_video_views_for_ntiid(video,
                                                   user=user,
                                                   course=course,
                                                   order_by='timestamp',
                                                   limit=1)
    most_recent_event = most_recent_watch[0] if most_recent_watch else None
    if not most_recent_event:
        return None

    # We have at least a most_recent watch event, which means by definition
    # we have at least some segments. Fetch those now.

    segments = get_watched_segments_for_ntiid(video, user=user, course=course) if video else None

    assert segments, "VideoEvents but no segments"

    if segments:
        max_time = int(video.max_time_length) if video.max_time_length else None
        watched = _compute_watched_seconds(segments)
        last_mod = _get_last_mod(most_recent_event.timestamp)
        last_end_time = most_recent_event.VideoEndTime
        progress = VideoProgress(NTIID=resource_ntiid,
                                 AbsoluteProgress=min(watched, max_time) if max_time else watched,
                                 MaxPossibleProgress=max_time,
                                 LastModified=last_mod,
                                 HasProgress=True,
                                 Item=item,
                                 User=user,
                                 CompletionContext=course,
                                 MostRecentEndTime=last_end_time)
    return progress


def _get_last_mod_progress(values, id_val, item, user, course):
    """
    For a collection of items, gather progress based on last modified
    timestamp.

    Used in tests.
    """
    progress = None
    if values:
        last_mod = max(x.timestamp for x in values)
        last_mod = _get_last_mod(last_mod)
        progress = Progress(NTIID=id_val,
                            AbsoluteProgress=None,
                            MaxPossibleProgress=None,
                            LastModified=last_mod,
                            Item=item,
                            User=user,
                            CompletionContext=course,
                            HasProgress=True)
    return progress

