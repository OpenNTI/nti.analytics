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

from dolmen.builtins.interfaces import IDict
from dolmen.builtins.interfaces import IList
from dolmen.builtins.interfaces import IString
from dolmen.builtins.interfaces import INumeric
from dolmen.builtins.interfaces import IUnicode
from dolmen.builtins.interfaces import IIterable

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItem

from nti.assessment.interfaces import IQAssessedQuestionSet

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.interfaces import IUser

from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import Choice
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
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

	def init( obj ):
		"""
		Does analytic processing for the given object.
		"""

class IAnalyticsObjectBase(interface.Interface):
	timestamp = Number(title=u"The timestamp when this event occurred, in seconds since epoch.",
						default=0.0,
						required=True )

	user = ValidTextLine(title='User who created the event', required=False)
	SessionID = Number( title=u"The analytics session id.", required=False )

class ITimeLength(interface.Interface):

	Duration = Number(title=u"The time length of the event, in seconds", default=0)

class IAnalyticsViewEvent(IAnalyticsObjectBase, ITimeLength):
	"""
	A basic analytics viewing event.
	"""
	pass

class IBlogViewEvent(IAnalyticsViewEvent):
	"""
	A blog viewing event.
	"""
	blog_id = ValidTextLine(title="The blog ntiid.")

class ICourseEvent(interface.Interface):
	"""
	A course event.
	"""
	RootContextID = ValidTextLine(title='Course ntiid')

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
	event_type = Choice(vocabulary=VIDEO_EVENTS_VOCABULARY,
					    title='The type of video event', required=True)

	video_start_time = Number(title=u"The point in the video that starts playing, in seconds.",
							default=0)

	video_end_time = Number(title=u"The point at which the video stops playing, in seconds.",
							default=0)

	MaxDuration = Number(title=u"The maximum length of the video, in seconds.",
							required=False)

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
	An analytics forum comment.
	"""
	CommentLength = Number(title=u"The character length of the comment.", default=0, required=False)

	Comment = Object( IPost, title=u"The underlying comment for this object.", required=True )

class IAnalyticsAssessment(IAnalyticsObjectBase, ITimeLength, ICourseEvent):
	"""
	An analytics self-assessment taken record.
	"""
	Submission = Object( IQAssessedQuestionSet, title=u"The underlying submission for this object.",
						required=True )

class IAssessmentGrade(interface.Interface):
	"""
	The analytics grade information.
	"""
	GradeNum = Number( title=u"The numerical value of the grade.", required=False )

	Grade = ValidTextLine( title=u"The textual value of the grade.", required=False )

	Grader = ValidTextLine( title=u"The user who graded the assignment", required=False )

	IsCorrect = Bool( title=u"Whether the object could be considered correct.", required=False )

class IAnalyticsAssignmentDetail( ITimeLength, IAssessmentGrade ):

	QuestionId = ValidTextLine( title=u"The question ntiid.", required=True )
	QuestionPartId = Number( title=u"The question part index.", required=True )
	Answer = Variant( (Object(IString),
						Object(INumeric),
						Object(IDict),
						Object(IList),
						Object(IUnicode) ),
					variant_raise_when_schema_provided=True,
					title=u"The user submission for this question part.", required=True )


class IAnalyticsAssignment(IAnalyticsObjectBase, ITimeLength, ICourseEvent, IAssessmentGrade):
	"""
	An analytics assignment taken record.
	"""
	Submission = Object( IUsersCourseAssignmentHistoryItem, title=u"The underlying submission for this object.",
									required=True )

	AssignmentId = ValidTextLine( title=u"The assessment identifier.", required=True )

	Details = TypedIterable(
		title="The detail parts of this assignment.",
		value_type=Object( IAnalyticsAssignmentDetail ),
		required=False )

class IAnalyticsSession(interface.Interface):
	"""
	The analytics logical session.
	"""
	SessionID = Number( title=u"The analytics session id.", required=False )

	SessionStartTime = Number( title=u"The timestamp when this sessiom started, in seconds since epoch.",
							required=False )

	SessionEndTime = Number( title=u"The timestamp when this session ended, in seconds since epoch.",
							required=False )

class IAnalyticsSessions(interface.Interface):
	"""
	A collection of analytics sessions.
	"""
	sessions = TypedIterable(title="The analytics sessions.",
							 value_type=Object( IAnalyticsSession ) )


class IProgress(interface.Interface):
	"""
	Indicates progress made on an underlying content unit.
	"""
	AbsoluteProgress = Number( title=u"A number indicating the absolute progress made on an item.",
							default=0 )

	MaxPossibleProgress = Number( title=u"A number indicating the max possible progress that could be made on an item. May be null.",
							default=0 )

	HasProgress = Bool( title=u"Indicates there was some progress made on item.",
					default=False )

class IUserResearchStatus(IDCTimes):
	"""
	Holds whether the user has accepted that data that they generate may be
	used for research.
	"""
	allow_research = Bool(title="Allow research on user's activity.",
						  required=False,
						  default=False )

class IUserResearchStatusEvent(IObjectEvent):
	"""
	Sent when a user updates their research status.
	"""
	user = Object(IUser, title="The user")
	allow_research = Bool( title="User allow_research status" )
