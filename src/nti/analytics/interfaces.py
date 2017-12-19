#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.schema import vocabulary

from zope.dublincore.interfaces import IDCTimes

from zope.interface.interfaces import IObjectEvent

from nti.base.interfaces import IIterable

from nti.dataserver.interfaces import IUser

from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import Choice
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import DateTime
from nti.schema.field import IndexedIterable as TypedIterable
from nti.schema.field import DecodingValidTextLine as ValidTextLine

DEFAULT_ANALYTICS_FREQUENCY = 60
DEFAULT_ANALYTICS_BATCH_SIZE = 100

VIDEO_SKIP = u'SKIP'
VIDEO_WATCH = u'WATCH'
VIDEO_EVENTS = (VIDEO_SKIP, VIDEO_WATCH)
VIDEO_EVENTS_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x)
								 for _x in VIDEO_EVENTS])


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

	user = ValidTextLine(title=u'User who created the event', required=False)
	SessionID = Number(title=u"The analytics session id.", required=False)


class ITimeLength(interface.Interface):

	Duration = Number(title=u"The time length of the event, in seconds", required=False)


class IAnalyticsEvent(IAnalyticsObjectBase):
	"""
	An analytics event.
	"""


class IPriorityProcessingAnalyticsEvent(interface.Interface):
	"""
	A marker interface for analytics events that are time-sensitive.
	"""

class IAnalyticsViewEvent(IAnalyticsEvent,
						  IPriorityProcessingAnalyticsEvent,
						  ITimeLength):
	"""
	A basic analytics viewing event.
	"""
	context_path = List(title=u'Context path',
						description=u'List of ntiid locations describing where the event occurred.',
						min_length=0,
						default=None,
						required=False,
						value_type=ValidTextLine(title=u'The ntiid context segment'))


class IBlogViewEvent(IAnalyticsViewEvent):
	"""
	A blog viewing event.
	"""
	blog_id = ValidTextLine(title=u"The blog ntiid.")


class IRootContextEvent(interface.Interface):
	"""
	An event rooted in a root context, typically an entity or course.
	"""
	RootContextID = ValidTextLine(title=u'Object ntiid', required=True)


class ITopicViewEvent(IAnalyticsViewEvent, IRootContextEvent):
	"""
	A topic viewing event.
	"""
	topic_id = ValidTextLine(title=u'Topic ntiid')


class IResourceEvent(IAnalyticsViewEvent, IRootContextEvent):
	"""
	Describes a resource viewing event.
	"""
	ResourceId = ValidTextLine(title=u"The resource ntiid.")


class IAssessmentViewEvent( IAnalyticsViewEvent, IRootContextEvent ):
	ResourceId = ValidTextLine(title=u"The assessment ntiid.", required=True)
	ContentId = ValidTextLine(title=u"The resource page ntiid.", required=False)


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
	note_id = ValidTextLine(title=u"The note ntiid.")


class IProfileViewEvent(IAnalyticsViewEvent):
	"""
	A profile viewing event.
	"""
	ProfileEntity = ValidTextLine(title=u"The profile entity username.", required=True)


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
						title=u'The type of video event',
						required=True)

	video_start_time = Number(title=u"The point in the video that starts playing, in seconds.",
							default=0)

	video_end_time = Number(title=u"The point at which the video stops playing, in seconds.",
							default=0, required=False)

	MaxDuration = Number(title=u"The maximum length of the video, in seconds.",
							required=False)

	with_transcript = Bool(title=u"Whether the video was viewed with a transcript or not.")

	PlaySpeed = Number(title=u"The play speed of the video", required=False)


class IVideoPlaySpeedChangeEvent(IAnalyticsEvent, IRootContextEvent):
	"""
	Describes when a user changes the video play speed.
	"""

	ResourceId = ValidTextLine(title=u"The resource ntiid.", required=True)

	OldPlaySpeed = Number(title=u"The old play speed of the video", required=True)

	NewPlaySpeed = Number(title=u"The new play speed of the video", required=True)

	VideoTime = Number(title=u"The point at which the video play speed changes, in seconds.",
						required=True)


class ICourseEvent(interface.Interface):
	"""
	A course event.
	"""

	RootContextID = ValidTextLine(title=u'Course ntiid', required=True)


class ICourseCatalogViewEvent(IAnalyticsViewEvent, ICourseEvent):
	"""
	Describes a course catalog viewing event.
	"""


class IBatchResourceEvents(IIterable):
	events = TypedIterable(title=u"The events in this batch",
						   value_type=Object(IAnalyticsEvent))


class IGeographicalLocation(interface.Interface):
	Latitude = ValidTextLine(title=u'The latitude of this session',
							 required=False)

	Longitude = ValidTextLine(title=u'The logitude of this session',
							 required=False)

	City = ValidTextLine(title=u'The gelocated city of this session',
							 required=False)

	State = ValidTextLine(title=u'The gelocated state of this session',
							 required=False)

	Country = ValidTextLine(title=u'The gelocated country of this session',
							 required=False)


class IAnalyticsSession(interface.Interface):
	"""
	The analytics logical session.
	"""

	SessionID = Number(title=u"The analytics session id.", required=False)

	SessionStartTime = Number(title=u"The timestamp when this sessiom started, in seconds since epoch.",
							required=False)

	SessionEndTime = Number(title=u"The timestamp when this session ended, in seconds since epoch.",
							required=False)

	Username = ValidTextLine(title=u'User this session belongs to',
							 required=False)
	Username.setTaggedValue('_ext_excluded_out', True)

	UserAgent = ValidTextLine(title=u'UserAgent this session came from',
							 required=False)
	UserAgent.setTaggedValue('_ext_excluded_out', True)

	GeographicalLocation = Object(IGeographicalLocation,
								  title=u'Geographical location data for this session',
								  required=False)
	GeographicalLocation.setTaggedValue('_ext_excluded_out', True)


class IAnalyticsSessions(interface.Interface):
	"""
	A collection of analytics sessions.
	"""
	sessions = TypedIterable(title=u"The analytics sessions.",
							 value_type=Object(IAnalyticsSession))


class IProgress(interface.Interface):
	"""
	Indicates progress made on underlying content.
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


class IVideoProgress(IProgress):
	"""
	Indicates progress made on a video.
	"""
	MostRecentEndTime = Number(title=u"A number indicating the last end point, in seconds, in which the video was watched.",
							   default=0)


class IUserResearchStatus(IDCTimes):
	"""
	Holds whether the user has accepted that data that they generate may be
	used for research.
	"""

	allow_research = Bool(title=u"Allow research on user's activity.",
						  required=False,
						  default=False)


class IUserResearchStatusEvent(IObjectEvent):
	"""
	Sent when a user updates their research status.
	"""

	user = Object(IUser, title=u"The user")
	allow_research = Bool(title=u"User allow_research status")


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


class AnalyticsEventValidationError(Exception):
	"""
	Raised when an event has invalid data.
	"""

class IAnalyticsSessionIdProvider(interface.Interface):
	"""
	An adapter to retrieve an analytics session id for an event.
	"""

	def get_session_id():
		"""
		Return the applicable session_id for this event.
		"""
