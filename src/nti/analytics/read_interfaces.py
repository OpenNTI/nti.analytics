#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema import vocabulary

from dolmen.builtins.interfaces import IDict
from dolmen.builtins.interfaces import IList
from dolmen.builtins.interfaces import IString
from dolmen.builtins.interfaces import INumeric
from dolmen.builtins.interfaces import IUnicode

from nti.analytics.interfaces import ITimeLength
from nti.analytics.interfaces import IAnalyticsViewEvent

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItem

from nti.assessment.interfaces import IQAssessedQuestionSet

from nti.contentlibrary.interfaces import IContentPackage
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.contenttypes.forums.interfaces import IGeneralForumComment
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost

from nti.dataserver.interfaces import IUser, IFriendsList
from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IBookmark

from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import Choice
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import DateTime
from nti.schema.field import DecodingValidTextLine as ValidTextLine
from nti.schema.field import IndexedIterable as TypedIterable

SHARING_ENUM = ( 'PUBLIC', 'COURSE', 'OTHER', 'UNKNOWN' )
SHARING_VOCAB = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in SHARING_ENUM])

class IAnalyticsObjectBase(interface.Interface):
	# Same as our inbound IAnalyticsObjectBase, except with a Datetime timestamp.
	timestamp = DateTime(title=u"The timestamp when this event occurred.",
						required=False)
	user = ValidTextLine(title='User who created the event', required=False)
	SessionID = Number(title=u"The analytics session id.", required=False)

class IAnalyticsSession(interface.Interface):
	SessionID = Number(title=u"The analytics session id.", required=False)
	SessionStartTime = DateTime(title=u"The timestamp when this session started.",
							required=False)
	SessionEndTime = DateTime(title=u"The timestamp when this session ended.",
							required=False)
	Duration = Number(title=u"The duration of the session, in seconds.", required=False)

class IAnalyticsGroup( IAnalyticsObjectBase ):
	"""
	An analytics group.
	"""
	Group = Object(IFriendsList, title=u"The underlying group for this object.", required=True)

class IRootContextMixin(interface.Interface):
	RootContext = Variant((	Object(ICourseInstance),
							Object(IContentPackage)),
							title='The underlying root context', required=True)

class IAnalyticsViewEvent(IAnalyticsObjectBase, ITimeLength):
	"""
	A basic analytics viewing event.
	"""
	context_path = List(title='Context path',
						description='List of ntiid locations describing where the event occurred.',
						min_length=0,
						default=None,
						required=False,
						value_type=ValidTextLine(title='The ntiid context segment'))

class IAnalyticsViewBase( IAnalyticsViewEvent, IRootContextMixin ):

	ResourceId = ValidTextLine(title="The resource ntiid.")

class IAnalyticsResourceView( IAnalyticsViewBase ):
	"""
	An analytics resource view.
	"""

class IAnalyticsSelfAssessmentView( IAnalyticsViewBase ):
	"""
	An analytics self assessment view.
	"""

class IAnalyticsAssignmentView( IAnalyticsViewBase ):
	"""
	An analytics assignment view.
	"""

class IAnalyticsVideoBase( IAnalyticsViewBase ):
	"""
	An analytics video view.
	"""

	VideoStartTime = Number(title=u"The point in the video that starts playing, in seconds.",
							default=0)

	VideoEndTime = Number(title=u"The point at which the video stops playing, in seconds.",
							default=0, required=False)

	MaxDuration = Number(title=u"The maximum length of the video, in seconds.",
							required=False)

	WithTranscript = Bool(title=u"Whether the video was viewed with a transcript or not.")

	PlaySpeed = Number(title="The play speed of the video", required=False)

class IAnalyticsVideoSkip( IAnalyticsVideoBase ):
	"""
	An analytics video skip.
	"""

class IAnalyticsVideoView( IAnalyticsVideoBase ):
	"""
	An analytics video view.
	"""

class IAnalyticsRatedObject(interface.Interface):
	"""
	Holds all ratings for this object.
	"""
	LikeCount = Number(title=u"The number of likes", default=0)
	FavoriteCount = Number(title=u"The number of favorites", default=0)
	Flagged = Bool(title=u"Whether the object is flagged/reported.", default=False)

class IAnalyticsBlog( IAnalyticsObjectBase, IAnalyticsRatedObject ):
	"""
	An analytics blog.
	"""
	BlogLength = Number(title=u"The character length of the blog.", default=0, required=False)
	Blog = Variant((Object(IPersonalBlogEntry),
					Object(IPersonalBlogEntryPost)),
					title='The underlying blog context', required=True)

class IReplyToMixin( interface.Interface ):
	IsReply = Bool(title=u"Whether the obj is a reply to another object.", required=True)
	RepliedToUser = Object(IUser, title="The creator of the replied to object.", required=False)

class IAnalyticsBlogComment(IAnalyticsObjectBase, IAnalyticsRatedObject, IReplyToMixin):
	"""
	An analytics forum comment.
	"""
	CommentLength = Number(title=u"The character length of the comment.", default=0, required=False)
	Comment = Object(IPersonalBlogComment, title=u"The underlying comment for this object.", required=True)

class IAnalyticsTopic(IAnalyticsObjectBase, IRootContextMixin, IAnalyticsRatedObject):
	"""
	An analytics topic.
	"""
	Topic = Object(ITopic, title='The underlying topic object.', required=True)

class IAnalyticsTopicView(IAnalyticsViewBase, IRootContextMixin):
	"""
	An analytics topic view.
	"""
	Topic = Object(ITopic, title='The underlying topic object.', required=True)

class IAnalyticsForumComment(IAnalyticsObjectBase, IRootContextMixin, IAnalyticsRatedObject, IReplyToMixin):
	"""
	An analytics forum comment.
	"""
	CommentLength = Number(title=u"The character length of the comment.", default=0, required=False)
	Comment = Object(IGeneralForumComment, title=u"The underlying comment for this object.", required=True)

class IAnalyticsAssessment(IAnalyticsObjectBase, ITimeLength, IRootContextMixin):
	"""
	An analytics self-assessment taken record.
	"""
	Submission = Object(IQAssessedQuestionSet, title=u"The underlying submission for this object.",
						required=True)
	AssessmentId = ValidTextLine(title=u"The assessment identifier.", required=True)

class IAssessmentGrade(interface.Interface):
	"""
	The analytics grade information.
	"""
	GradeNum = Number(title=u"The numerical value of the grade.", required=False)
	Grade = ValidTextLine(title=u"The textual value of the grade.", required=False)
	Grader = ValidTextLine(title=u"The user who graded the assignment", required=False)
	IsCorrect = Bool(title=u"Whether the object could be considered correct.", required=False)

class IAnalyticsAssignmentDetail(ITimeLength, IAssessmentGrade):

	QuestionId = ValidTextLine(title=u"The question ntiid.", required=True)
	QuestionPartId = Number(title=u"The question part index.", required=True)
	Answer = Variant((Object(IString),
						Object(INumeric),
						Object(IDict),
						Object(IList),
						Object(IUnicode)),
					variant_raise_when_schema_provided=True,
					title=u"The user submission for this question part.", required=True)

class IAnalyticsAssignment(IAnalyticsObjectBase, ITimeLength, IRootContextMixin, IAssessmentGrade):
	"""
	An analytics assignment taken record.
	"""
	Submission = Object(IUsersCourseAssignmentHistoryItem,
					title=u"The underlying submission for this object.", required=True)

	AssignmentId = ValidTextLine(title=u"The assessment identifier.", required=True)

	Details = TypedIterable(
		title="The detail parts of this assignment.",
		value_type=Object(IAnalyticsAssignmentDetail),
		required=False)

	IsLate = Bool(title=u"Whether the submitted assignment was late.", required=False)

class IAnalyticsTag(IAnalyticsObjectBase, IRootContextMixin):
	"""
	An analytics tag.
	"""

class IAnalyticsNote(IAnalyticsTag, IAnalyticsRatedObject, IReplyToMixin):
	"""
	An analytics note.
	"""
	Note = Object(INote, title='The underlying note object.', required=True)
	NoteLength = Number(title=u"The length of the body of the note.", required=True)
	Sharing = Choice(vocabulary=SHARING_VOCAB, title=u"A sharing enum", required=True)

class IAnalyticsHighlight(IAnalyticsTag):
	"""
	An analytics highlight.
	"""
	Highlight = Object(IHighlight, title='The underlying highlight object.', required=True)

class IAnalyticsBookmark(IAnalyticsTag):
	"""
	An analytics bookmark.
	"""
	Bookmark = Object(IBookmark, title='The underlying bookmark object.', required=True)

class IAnalyticsRating( IAnalyticsObjectBase ):
	"""
	An analytics rating.
	"""
	# Do we want or need context?
	ObjectCreator = Object(IUser, title="The creator of the rated object.", required=True)

class IAnalyticsLike( IAnalyticsRating ):
	"""
	Describes a recorded like event.
	"""

class IAnalyticsFavorite( IAnalyticsRating ):
	"""
	Describes a recorded favorite event..
	"""

class IAnalyticsContact( IAnalyticsObjectBase ):
	"""
	An analytics contact added..
	"""
	Contact = Object(IEntity, title='The contact added.', required=True)

