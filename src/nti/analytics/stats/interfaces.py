#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

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

	Count = Number(title="Count", required=True)

class IPostMixin(ICountStats):
	TopLevelCount = Number(title="The number of top level posts.", required=True)
	ReplyCount = Number(title="The number of reply posts.", required=True)
	DistinctPostsLiked = Number(title="The number of distinct posts liked.", required=True)
	DistinctPostsFavorited = Number(title="The number of distinct posts favorited.", required=True)
	TotalLikes = Number(title="The total number of posts liked.", required=True)
	TotalFavorites = Number(title="The total number of posts favorited.", required=True)
	RecursiveChildrenCount = Number(title="The total number of direct or indirect children of this post.",
									required=True)
	StandardDeviationLength = Float(title="Standard deviation body length", required=False)
	AverageLength = Float(title="Average body length", required=True)
	ContainsWhiteboardCount = Number(title="The total amount of time spent.", required=True)

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
	AggregateTime = Number(title="The total amount of time spent.", required=True)
	StandardDeviationDuration = Float(title="Standard deviation duration", required=False)
	AverageDuration = Float(title="Average duration", required=True)

class IUniqueStatsMixin(ICountStats):
	"""
	Establishes uniqueness counts.
	"""
	UniqueCount = Number(title="Unique self assessment count", required=True)

class ISelfAssessmentStats(IUniqueStatsMixin):
	"""
	A container for holding self-assessment stats.
	"""

class IAssignmentStats(IUniqueStatsMixin):
	"""
	A container for holding assignment stats.
	"""
	AssignmentLateCount = Number(title="Unique self assessment count", required=True)
	TimedAssignmentCount = Number(title="Unique assignment count", required=True)
	TimedAssignmentLateCount = Number(title="Late assignment timed count", required=True)

class IAnalyticsStatsSource(interface.Interface):
	"""
	A utility to provide stats.
	"""
