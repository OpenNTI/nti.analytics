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

from nti.analytics import interfaces

@interface.implementer(interfaces.IResourceEvent)
@WithRepr
class ResourceEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.IResourceEvent)

	__external_can_create__ = True
	__external_class_name__ = "ResourceEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.resourceevent'

@interface.implementer(interfaces.IVideoEvent)
@WithRepr
class WatchVideoEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.IVideoEvent)

	__external_can_create__ = True
	__external_class_name__ = "WatchVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.watchvideoevent'
	event_type = 'WATCH'

@interface.implementer(interfaces.IVideoEvent)
@WithRepr
class SkipVideoEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.IVideoEvent)

	__external_can_create__ = True
	__external_class_name__ = "SkipVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.skipvideoevent'
	event_type = 'SKIP'

@interface.implementer(interfaces.ICourseCatalogViewEvent)
@WithRepr
class CourseCatalogViewEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.ICourseCatalogViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "CourseCatalogViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.coursecatalogviewevent'

@interface.implementer(interfaces.IBlogViewEvent)
@WithRepr
class BlogViewEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.IBlogViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "BlogViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.blogviewevent'

@interface.implementer(interfaces.INoteViewEvent)
@WithRepr
class NoteViewEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.INoteViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "NoteViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.noteviewevent'

@interface.implementer(interfaces.ITopicViewEvent)
@WithRepr
class TopicViewEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.ITopicViewEvent)

	__external_can_create__ = True
	__external_class_name__ = "TopicViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.topicviewevent'

@interface.implementer(interfaces.IBatchResourceEvents)
@WithRepr
@NoPickle
class BatchResourceEvents(SchemaConfigured):
	createDirectFieldProperties(interfaces.IBatchResourceEvents)

	__external_can_create__ = True
	__external_class_name__ = "BatchResourceEvents"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.batchevents'

	def __iter__(self):
		return iter( self.events )

	def __len__(self):
		return len( self.events )


@interface.implementer(interfaces.IAnalyticsTopic)
@WithRepr
class AnalyticsTopic(SchemaConfigured):
	createDirectFieldProperties(interfaces.IAnalyticsTopic)

	__external_can_create__ = False
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticstopic'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(interfaces.IAnalyticsForumComment)
@WithRepr
class AnalyticsForumComment(SchemaConfigured):
	createDirectFieldProperties(interfaces.IAnalyticsForumComment)

	__external_can_create__ = False
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsforumcomment'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
