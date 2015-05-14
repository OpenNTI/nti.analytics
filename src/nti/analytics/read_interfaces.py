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
from nti.analytics.interfaces import IAnalyticsObjectBase

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItem

from nti.assessment.interfaces import IQAssessedQuestionSet

from nti.contentlibrary.interfaces import IContentPackage
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IBookmark

from nti.schema.field import Bool
from nti.schema.field import Choice
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import DecodingValidTextLine as ValidTextLine
from nti.schema.field import IndexedIterable as TypedIterable

SHARING_ENUM = ( 'PUBLIC', 'COURSE', 'OTHER', 'UNKNOWN' )
SHARING_VOCAB = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in SHARING_ENUM])

class IRootContextMixin(interface.Interface):
	RootContext = Variant((	Object(ICourseInstance),
							Object(IContentPackage)),
							title='The underlying root context', required=True)

class IAnalyticsViewBase( IAnalyticsViewEvent, IRootContextMixin ):

	ResourceId = ValidTextLine(title="The resource ntiid.")

class IAnalyticsResourceView( IAnalyticsViewBase ):
	"""
	An analytics resource view.
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

class IAnalyticsTopic(IAnalyticsObjectBase, IRootContextMixin):
	"""
	An analytics topic.
	"""
	Topic = Object(ITopic, title='The underlying topic object.', required=True)

class IAnalyticsTopicView(IAnalyticsViewBase, IRootContextMixin):
	"""
	An analytics topic view.
	"""
	Topic = Object(ITopic, title='The underlying topic object.', required=True)

class IAnalyticsForumComment(IAnalyticsObjectBase, IRootContextMixin, IAnalyticsRatedObject):
	"""
	An analytics forum comment.
	"""
	CommentLength = Number(title=u"The character length of the comment.", default=0, required=False)
	Comment = Object(IPost, title=u"The underlying comment for this object.", required=True)

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

class IAnalyticsNote(IAnalyticsTag, IAnalyticsRatedObject):
	"""
	An analytics note.
	"""
	Note = Object(INote, title='The underlying note object.', required=True)
	NoteLength = Number(title=u"The length of the body of the note.", required=True)
	Sharing = Choice(vocabulary=SHARING_VOCAB, title=u"A sharing enum", required=True)
	IsReply = Bool(title=u"Whether the note is a reply to another note.", required=True)

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

