#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from nti.externalization.representation import WithRepr

from nti.common.property import alias

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.analytics.read_interfaces import IAnalyticsBlog
from nti.analytics.read_interfaces import IAnalyticsContact
from nti.analytics.read_interfaces import IAnalyticsBlogComment
from nti.analytics.read_interfaces import IAnalyticsTopic
from nti.analytics.read_interfaces import IAnalyticsTopicView
from nti.analytics.read_interfaces import IAnalyticsAssessment
from nti.analytics.read_interfaces import IAnalyticsAssignment
from nti.analytics.read_interfaces import IAnalyticsForumComment
from nti.analytics.read_interfaces import IAnalyticsAssignmentDetail
from nti.analytics.read_interfaces import IAnalyticsNote
from nti.analytics.read_interfaces import IAnalyticsHighlight
from nti.analytics.read_interfaces import IAnalyticsBookmark
from nti.analytics.read_interfaces import IAnalyticsResourceView
from nti.analytics.read_interfaces import IAnalyticsVideoView
from nti.analytics.read_interfaces import IAnalyticsVideoSkip
from nti.analytics.read_interfaces import IAnalyticsLike
from nti.analytics.read_interfaces import IAnalyticsFavorite
from nti.analytics.read_interfaces import IAnalyticsSelfAssessmentView
from nti.analytics.read_interfaces import IAnalyticsAssignmentView
from nti.analytics.read_interfaces import IAnalyticsSession

class BaseAnalyticsMixin(SchemaConfigured):
	__external_can_create__ = False

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IAnalyticsTopic)
@WithRepr
class AnalyticsTopic(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsTopic)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticstopic'

@interface.implementer(IAnalyticsForumComment)
@WithRepr
class AnalyticsForumComment(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsForumComment)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsforumcomment'

@interface.implementer(IAnalyticsAssessment)
@WithRepr
class AnalyticsAssessment(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsAssessment)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsassessment'

@interface.implementer(IAnalyticsAssignment)
@WithRepr
class AnalyticsAssignment(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsAssignment)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsassignment'

@interface.implementer(IAnalyticsAssignmentDetail)
@WithRepr
class AnalyticsAssignmentDetail(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsAssignmentDetail)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsassignmentdetail'

@interface.implementer(IAnalyticsNote)
@WithRepr
class AnalyticsNote(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsNote)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsnote'

@interface.implementer(IAnalyticsHighlight)
@WithRepr
class AnalyticsHighlight(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsHighlight)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticshighlight'

@interface.implementer(IAnalyticsBookmark)
@WithRepr
class AnalyticsBookmark(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsBookmark)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsbookmark'

@interface.implementer(IAnalyticsLike)
@WithRepr
class AnalyticsLike(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsLike)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticslike'

@interface.implementer(IAnalyticsFavorite)
@WithRepr
class AnalyticsFavorite(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsFavorite)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsfavorite'

@interface.implementer(IAnalyticsBlog)
@WithRepr
class AnalyticsBlog(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsBlog)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsblog'

@interface.implementer(IAnalyticsBlogComment)
@WithRepr
class AnalyticsBlogComment(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsBlogComment)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsblogcomment'

@interface.implementer(IAnalyticsContact)
@WithRepr
class AnalyticsContact(BaseAnalyticsMixin):
	createDirectFieldProperties(IAnalyticsContact)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticscontact'



class BaseAnalyticsDurationMixin(SchemaConfigured):
	__external_can_create__ = False

	time_length = alias('Duration')

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IAnalyticsVideoView)
@WithRepr
class AnalyticsVideoView(BaseAnalyticsDurationMixin):
	createDirectFieldProperties(IAnalyticsVideoView)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsvideoview'

@interface.implementer(IAnalyticsVideoSkip)
@WithRepr
class AnalyticsVideoSkip(BaseAnalyticsDurationMixin):
	createDirectFieldProperties(IAnalyticsVideoSkip)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsvideoskip'

@interface.implementer(IAnalyticsResourceView)
@WithRepr
class AnalyticsResourceView(BaseAnalyticsDurationMixin):
	createDirectFieldProperties(IAnalyticsResourceView)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsresourceview'

@interface.implementer(IAnalyticsSelfAssessmentView)
@WithRepr
class AnalyticsSelfAssessmentView(BaseAnalyticsDurationMixin):
	createDirectFieldProperties(IAnalyticsSelfAssessmentView)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsselfassessmentview'

@interface.implementer(IAnalyticsAssignmentView)
@WithRepr
class AnalyticsAssignmentView(BaseAnalyticsDurationMixin):
	createDirectFieldProperties(IAnalyticsAssignmentView)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsassignmentview'

@interface.implementer(IAnalyticsTopicView)
@WithRepr
class AnalyticsTopicView(BaseAnalyticsDurationMixin):
	createDirectFieldProperties(IAnalyticsTopicView)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticstopicview'

@interface.implementer(IAnalyticsSession)
@WithRepr
class AnalyticsSession(BaseAnalyticsDurationMixin):
	createDirectFieldProperties(IAnalyticsSession)
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticssession'
