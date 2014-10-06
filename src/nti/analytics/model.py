#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.externalization.persistence import NoPickle
from nti.externalization.representation import WithRepr

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.analytics.interfaces import VIDEO_SKIP
from nti.analytics.interfaces import VIDEO_WATCH

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IBlogViewEvent
from nti.analytics.interfaces import INoteViewEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import IAnalyticsTopic
from nti.analytics.interfaces import ITopicViewEvent
from nti.analytics.interfaces import IAnalyticsSession
from nti.analytics.interfaces import IAnalyticsSessions
from nti.analytics.interfaces import IAnalyticsAssessment
from nti.analytics.interfaces import IAnalyticsAssignment
from nti.analytics.interfaces import IBatchResourceEvents
from nti.analytics.interfaces import IAnalyticsForumComment
from nti.analytics.interfaces import ICourseCatalogViewEvent
from nti.analytics.interfaces import IAnalyticsAssignmentDetail

@interface.implementer(IResourceEvent)
@WithRepr
class ResourceEvent(SchemaConfigured):
	createDirectFieldProperties(IResourceEvent)

	__external_can_create__ = True
	__external_class_name__ = "ResourceEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.resourceevent'

@interface.implementer(IVideoEvent)
@WithRepr
class WatchVideoEvent(SchemaConfigured):
	createDirectFieldProperties(IVideoEvent)

	__external_can_create__ = True
	__external_class_name__ = "WatchVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.watchvideoevent'
	event_type = VIDEO_WATCH

@interface.implementer(IVideoEvent)
@WithRepr
class SkipVideoEvent(SchemaConfigured):
	createDirectFieldProperties(IVideoEvent)

	__external_can_create__ = True
	__external_class_name__ = "SkipVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.skipvideoevent'
	event_type = VIDEO_SKIP

@interface.implementer(ICourseCatalogViewEvent)
@WithRepr
class CourseCatalogViewEvent(SchemaConfigured):
	createDirectFieldProperties(ICourseCatalogViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "CourseCatalogViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.coursecatalogviewevent'

@interface.implementer(IBlogViewEvent)
@WithRepr
class BlogViewEvent(SchemaConfigured):
	createDirectFieldProperties(IBlogViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "BlogViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.blogviewevent'

@interface.implementer(INoteViewEvent)
@WithRepr
class NoteViewEvent(SchemaConfigured):
	createDirectFieldProperties(INoteViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "NoteViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.noteviewevent'

@interface.implementer(ITopicViewEvent)
@WithRepr
class TopicViewEvent(SchemaConfigured):
	createDirectFieldProperties(ITopicViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "TopicViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.topicviewevent'

@interface.implementer(IBatchResourceEvents)
@WithRepr
@NoPickle
class BatchResourceEvents(SchemaConfigured):
	createDirectFieldProperties(IBatchResourceEvents)

	__external_can_create__ = True
	__external_class_name__ = "BatchResourceEvents"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.batchevents'

	def __iter__(self):
		return iter( self.events )

	def __len__(self):
		return len( self.events )


@interface.implementer(IAnalyticsTopic)
@WithRepr
class AnalyticsTopic(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsTopic)

	__external_can_create__ = False
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticstopic'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IAnalyticsForumComment)
@WithRepr
class AnalyticsForumComment(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsForumComment)

	__external_can_create__ = False
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsforumcomment'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IAnalyticsAssessment)
@WithRepr
class AnalyticsAssessment(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsAssessment)

	__external_can_create__ = False
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsassessment'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IAnalyticsAssignment)
@WithRepr
class AnalyticsAssignment(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsAssignment)

	__external_can_create__ = False
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsassignment'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IAnalyticsAssignmentDetail)
@WithRepr
class AnalyticsAssignmentDetail(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsAssignmentDetail)

	__external_can_create__ = False
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsassignmentdetail'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IAnalyticsSessions)
@WithRepr
@NoPickle
class AnalyticsSessions(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsSessions)

	__external_can_create__ = True
	__external_class_name__ = "AnalyticsSessions"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticssessions'

	def __iter__(self):
		return iter( self.sessions )

	def __len__(self):
		return len( self.sessions )

@interface.implementer(IAnalyticsSession)
@WithRepr
class AnalyticsSession(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsSession)

	__external_can_create__ = True
	__external_class_name__ = "AnalyticsSession"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticssession'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
