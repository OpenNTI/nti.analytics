#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import DecodingValidTextLine as ValidTextLine
from nti.schema.field import IndexedIterable as TypedIterable

from dolmen.builtins.interfaces import IIterable

from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IPost

class IAnalyticsQueueFactory(interface.Interface):
	"""
	A factory for analytics processing queues.
	"""

class IObjectProcessor(interface.Interface):

	def init( obj ):
		"""
		Does analytic processing for the given object.
		"""
class IAnalyticsObjectBase(interface.Interface):
	timestamp = Number(title=u"The timestamp when this event occurred, in seconds since epoch.",
						default=0.0,
						required=True )

	user = ValidTextLine(title='User who created the event', required=True )

class IAnalyticsViewEvent(IAnalyticsObjectBase):
	"""
	A basic analytics viewing event.
	"""
	time_length = Number(title=u"The time length of the event, in seconds",
						default=0)

class IBlogViewEvent(IAnalyticsViewEvent):
	"""
	A blog viewing event.
	"""
	blog_id = ValidTextLine(title="The blog ntiid.")

class ICourseEvent(interface.Interface):
	"""
	A course event.
	"""
	course = ValidTextLine(title='Course ntiid')

class ITopicViewEvent(IAnalyticsViewEvent, ICourseEvent):
	"""
	A topic viewing event.
	"""
	topic_id = ValidTextLine(title='Topic ntiid')

class IResourceEvent(IAnalyticsViewEvent, ICourseEvent):
	"""
	Describes a resource viewing event.
	"""
	context_path = List(title='Context path',
						description='List of ntiid locations describing where the event occurred.',
						min_length=0,
						value_type=ValidTextLine( title='The ntiid context segment'))

	resource_id = ValidTextLine(title="The resource ntiid.")

class INoteViewEvent(IAnalyticsViewEvent, ICourseEvent):
	"""
	A note viewing event.
	"""
	note_id = ValidTextLine(title="The note ntiid.")

class IVideoEvent(IResourceEvent):
	"""
	Describes a video event.
	"""
	event_type = ValidTextLine(title='The type of video event {WATCH, SKIP}')

	video_start_time = Number(title=u"The point in the video that starts playing, in seconds.",
							default=0)

	video_end_time = Number(title=u"The point at which the video stops playing, in seconds.",
							default=0)

	with_transcript = Bool(title=u"Whether the video was viewed with a transcript or not.")

class ICourseCatalogViewEvent(IAnalyticsViewEvent, ICourseEvent):
	"""
	Describes a course catalog viewing event.
	"""

class IBatchResourceEvents( IIterable ):
	events = TypedIterable(
		title="The events in this batch",
		value_type=Object( IAnalyticsViewEvent ) )


class IAnalyticsRatings(interface.Interface):
	"""
	Holds all ratings for this object.
	"""
	LikeCount = Number(title=u"The number of likes", default=0)

	FavoriteCount = Number(title=u"The number of favorites", default=0)

	Flagged = Bool(title=u"Whether the object is flagged/reported.", default=False)

class IAnalyticsTopic(IAnalyticsObjectBase, ICourseEvent):
	"""
	An analytics topic.
	"""
	Topic = Object( ITopic, title='The underlying topic object.', required=True )

class IAnalyticsForumComment(IAnalyticsObjectBase, ICourseEvent, IAnalyticsRatings):
	"""
	An analytics forum comment..
	"""
	CommentLength = Number(title=u"The character length of the comment.", default=0, required=False)

	Comment = Object( IPost, title=u"The underlying comment for this object.", required=True )
