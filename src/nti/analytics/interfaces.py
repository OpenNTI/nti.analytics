#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema import vocabulary

from zope.dublincore.interfaces import IDCTimes
from zope.interface.interfaces import IObjectEvent

from dolmen.builtins.interfaces import IIterable

from nti.dataserver.interfaces import IUser

from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import Choice
from nti.schema.field import DateTime
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import DecodingValidTextLine as ValidTextLine
from nti.schema.field import IndexedIterable as TypedIterable

VIDEO_SKIP = u'SKIP'
VIDEO_WATCH = u'WATCH'
VIDEO_EVENTS = (VIDEO_SKIP, VIDEO_WATCH)
VIDEO_EVENTS_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in VIDEO_EVENTS])

class IAnalyticsQueueFactory(interface.Interface):
	"""
	A factory for analytics processing queues.
	"""

class IObjectProcessor(interface.Interface):

	def init(obj):
		"""
		Does analytic processing for the given object.
		"""

class IAnalyticsObjectBase(interface.Interface):
	timestamp = Number(title=u"The timestamp when this event occurred, in seconds since epoch.",
						default=0.0,
						required=True)

	user = ValidTextLine(title='User who created the event', required=False)
	SessionID = Number(title=u"The analytics session id.", required=False)

class ITimeLength(interface.Interface):

	Duration = Number(title=u"The time length of the event, in seconds", required=False)

class IAnalyticsEvent(IAnalyticsObjectBase):
	"""An analytics event."""

class IAnalyticsViewEvent(IAnalyticsEvent, ITimeLength):
	"""
	A basic analytics viewing event.
	"""
	context_path = List(title='Context path',
						description='List of ntiid locations describing where the event occurred.',
						min_length=0,
						default=None,
						required=False,
						value_type=ValidTextLine(title='The ntiid context segment'))

class IBlogViewEvent(IAnalyticsViewEvent):
	"""
	A blog viewing event.
	"""
	blog_id = ValidTextLine(title="The blog ntiid.")

class IRootContextEvent(interface.Interface):
	"""
	An event rooted in a root context, typically an entity or course.
	"""
	RootContextID = ValidTextLine(title='Object ntiid', required=False)

class ITopicViewEvent(IAnalyticsViewEvent, IRootContextEvent):
	"""
	A topic viewing event.
	"""
	topic_id = ValidTextLine(title='Topic ntiid')

class IResourceEvent(IAnalyticsViewEvent, IRootContextEvent):
	"""
	Describes a resource viewing event.
	"""
	resource_id = ValidTextLine(title="The resource ntiid.")

class IAssessmentViewEvent( IAnalyticsViewEvent, IRootContextEvent ):
	ResourceId = ValidTextLine(title="The assessment ntiid.", required=True)
	ContentId = ValidTextLine(title="The resource page ntiid.", required=False)

class ISelfAssessmentViewEvent( IAssessmentViewEvent ):
	"""
	Describes a self-assessment viewing event.
	"""

class IAssignmentViewEvent( IAssessmentViewEvent ):
	"""
	Describes an assignment viewing event.
	"""

class INoteViewEvent(IAnalyticsViewEvent, IRootContextEvent):
	"""
	A note viewing event.
	"""
	note_id = ValidTextLine(title="The note ntiid.")

class IProfileViewEvent(IAnalyticsViewEvent):
	"""
	A profile viewing event.
	"""
	ProfileEntity = ValidTextLine(title="The profile entity username.", required=True)

class IProfileActivityViewEvent(IProfileViewEvent):
	"""
	A profile activity viewing event.
	"""

class IProfileMembershipViewEvent(IProfileViewEvent):
	"""
	A profile membership viewing event.
	"""

class IVideoEvent(IResourceEvent):
	"""
	Describes a video event.
	"""
	event_type = Choice(vocabulary=VIDEO_EVENTS_VOCABULARY,
					    title='The type of video event', required=True)

	video_start_time = Number(title=u"The point in the video that starts playing, in seconds.",
							default=0)

	video_end_time = Number(title=u"The point at which the video stops playing, in seconds.",
							default=0, required=False)

	MaxDuration = Number(title=u"The maximum length of the video, in seconds.",
							required=False)

	with_transcript = Bool(title=u"Whether the video was viewed with a transcript or not.")

	PlaySpeed = Number(title="The play speed of the video", required=False)

class IVideoPlaySpeedChangeEvent(IAnalyticsEvent, IRootContextEvent):
	"""
	Describes when a user changes the video play speed.
	"""
	ResourceId = ValidTextLine(title="The resource ntiid.", required=True)

	OldPlaySpeed = Number(title="The old play speed of the video", required=True)

	NewPlaySpeed = Number(title="The new play speed of the video", required=True)

	VideoTime = Number(title="The point at which the video play speed changes, in seconds.",
						required=True)

class ICourseEvent(interface.Interface):
	"""
	A course event.
	"""
	RootContextID = ValidTextLine(title='Course ntiid', required=True)

class ICourseCatalogViewEvent(IAnalyticsViewEvent, ICourseEvent):
	"""
	Describes a course catalog viewing event.
	"""

class IBatchResourceEvents(IIterable):
	events = TypedIterable(
		title="The events in this batch",
		value_type=Object(IAnalyticsEvent))

class IAnalyticsSession(interface.Interface):
	"""
	The analytics logical session.
	"""
	SessionID = Number(title=u"The analytics session id.", required=False)

	SessionStartTime = Number(title=u"The timestamp when this sessiom started, in seconds since epoch.",
							required=False)

	SessionEndTime = Number(title=u"The timestamp when this session ended, in seconds since epoch.",
							required=False)

class IAnalyticsSessions(interface.Interface):
	"""
	A collection of analytics sessions.
	"""
	sessions = TypedIterable(title="The analytics sessions.",
							 value_type=Object(IAnalyticsSession))


class IProgress(interface.Interface):
	"""
	Indicates progress made on an underlying content unit.
	"""
	AbsoluteProgress = Number(title=u"A number indicating the absolute progress made on an item.",
							default=0)

	MaxPossibleProgress = Number(title=u"A number indicating the max possible progress that could be made on an item. May be null.",
							default=0)

	HasProgress = Bool(title=u"Indicates there was some progress made on item.",
					default=False)

	ResourceID = ValidTextLine(title=u"The ntiid of the object who's progress this object represents.", required=True)

	LastModified = DateTime(title=u"The timestamp when this event occurred.",
						required=False)

class IUserResearchStatus(IDCTimes):
	"""
	Holds whether the user has accepted that data that they generate may be
	used for research.
	"""
	allow_research = Bool(title="Allow research on user's activity.",
						  required=False,
						  default=False)

class IUserResearchStatusEvent(IObjectEvent):
	"""
	Sent when a user updates their research status.
	"""
	user = Object(IUser, title="The user")
	allow_research = Bool(title="User allow_research status")

DEFAULT_ANALYTICS_FREQUENCY = 60
DEFAULT_ANALYTICS_BATCH_SIZE = 100

class IAnalyticsClientParams(interface.Interface):
	"""
	Defines parameters clients may use when deciding how often
	to PUT data to analytics.
	"""
	RecommendedBatchEventsSize = Number(title=u"How many events the client should send in a single batch_events call",
										required=False,
										default=DEFAULT_ANALYTICS_BATCH_SIZE)

	RecommendedBatchEventsSendFrequency = Number(title=u"How often the client should send batch events, in seconds.",
							required=False,
							default=DEFAULT_ANALYTICS_FREQUENCY)

	RecommendedBatchSessionsSize = Number(title=u"How many sessions the client should send in a single batch_events call",
										required=False,
										default=DEFAULT_ANALYTICS_BATCH_SIZE)

	RecommendedBatchSessionsSendFrequency = Number(title=u"How often the client should send session events, in seconds.",
							required=False,
							default=DEFAULT_ANALYTICS_FREQUENCY)

	RecommendedAnalyticsSyncInterval = Number(title=u"How often the client should sync sessions and events, in seconds.",
							required=False,
							default=DEFAULT_ANALYTICS_FREQUENCY)
