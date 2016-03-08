#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.common.property import alias

from nti.analytics.stats.interfaces import ICountStats
from nti.analytics.stats.interfaces import INoteStats
from nti.analytics.stats.interfaces import ITimeStats
from nti.analytics.stats.interfaces import ICommentStats
from nti.analytics.stats.interfaces import IAssignmentStats
from nti.analytics.stats.interfaces import IThoughtCommentStats
from nti.analytics.stats.interfaces import ISelfAssessmentStats

from nti.schema.field import SchemaConfigured

from nti.schema.schema import EqHash

@EqHash('count')
@interface.implementer(ICountStats)
class CountStats(SchemaConfigured):

	count = alias('Count')
	__external_class_name__ = "CountStats"
	mime_type = mimeType = 'application/vnd.nextthought.learningnetwork.stats'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@EqHash('aggregate_time', 'average', 'std_dev', 'count')
@interface.implementer(ITimeStats)
class TimeStats(CountStats):
	aggregate_time = alias('AggregateTime')
	std_dev = alias('StandardDeviationDuration')
	average = alias('AverageDuration')
	__external_class_name__ = "TimeStats"
	mime_type = mimeType = 'application/vnd.nextthought.learningnetwork.timestats'

@EqHash('Count', 'UniqueCount')
@interface.implementer(ISelfAssessmentStats)
class SelfAssessmentStats(CountStats):
	__external_class_name__ = "SelfAssessmentStats"
	mime_type = mimeType = 'application/vnd.nextthought.learningnetwork.selfassessmentstats'

@EqHash('Count', 'UniqueCount', 'AssignmentLateCount',
		'TimedAssignmentCount', 'TimedAssignmentLateCount')
@interface.implementer(IAssignmentStats)
class AssignmentStats(CountStats):
	__external_class_name__ = "AssignmentStats"
	mime_type = mimeType = 'application/vnd.nextthought.learningnetwork.assignmentstats'

@EqHash('Count', 'TopLevelCount', 'ReplyCount',
		'DistinctPostsLiked', 'DistinctPostsFavorited',
		'TotalLikes', 'TotalFavorites', 'RecursiveChildrenCount',
		'StandardDeviationLength', 'AverageLength', 'ContainsWhiteboardCount')
class PostStats(CountStats):
	pass

@interface.implementer(INoteStats)
class NoteStats(PostStats):
	__external_class_name__ = "NoteStats"
	mime_type = mimeType = 'application/vnd.nextthought.learningnetwork.notestats'

@interface.implementer(ICommentStats)
class CommentStats(PostStats):
	__external_class_name__ = "CommentStats"
	mime_type = mimeType = 'application/vnd.nextthought.learningnetwork.commentstats'

@interface.implementer(IThoughtCommentStats)
class ThoughtCommentStats(PostStats):
	__external_class_name__ = "ThoughtCommentStats"
	mime_type = mimeType = 'application/vnd.nextthought.learningnetwork.thoughtcommentstats'

