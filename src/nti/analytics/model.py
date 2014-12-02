#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.annotation.factory import factory as an_factory
from zope.interface.interfaces import ObjectEvent

from nti.externalization.persistence import NoPickle
from nti.externalization.representation import WithRepr

from nti.utils.property import alias

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
from nti.analytics.interfaces import IUserResearchStatus
from nti.analytics.interfaces import IUserResearchStatusEvent

from nti.dataserver.interfaces import IUser

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

def _replace_state(obj, old, new):
	if old in obj.__dict__:
		value = obj.__dict__.pop(old)
		if obj.__dict__.get(new, None) is None:
			obj.__dict__[new] = value

@WithRepr
class ViewEvent(SchemaConfigured):

	__external_can_create__ = True
	time_length = alias('Duration')

	def __setstate__(self, data):
		self.__dict__ = data
		_replace_state(self, 'time_length', 'Duration')

class RootContextEvent(ViewEvent): # alias

	course = alias('RootContextID')

	def __setstate__(self, data):
		self.__dict__ = data
		_replace_state(self, 'time_length', 'Duration')
		_replace_state(self, 'course', 'RootContextID')

@interface.implementer(IResourceEvent)
class ResourceEvent(RootContextEvent):
	createDirectFieldProperties(IResourceEvent)

	__external_class_name__ = "ResourceEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.resourceevent'

@interface.implementer(IVideoEvent)
class WatchVideoEvent(RootContextEvent):
	createDirectFieldProperties(IVideoEvent)

	__external_class_name__ = "WatchVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.watchvideoevent'
	event_type = VIDEO_WATCH

	course = alias('RootContextID')

@interface.implementer(IVideoEvent)
class SkipVideoEvent(RootContextEvent):
	createDirectFieldProperties(IVideoEvent)

	__external_class_name__ = "SkipVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.skipvideoevent'
	event_type = VIDEO_SKIP

	course = alias('RootContextID')

@interface.implementer(ICourseCatalogViewEvent)
class CourseCatalogViewEvent(RootContextEvent):
	createDirectFieldProperties(ICourseCatalogViewEvent)

	__external_class_name__ = "CourseCatalogViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.coursecatalogviewevent'

@interface.implementer(IBlogViewEvent)
class BlogViewEvent(ViewEvent):
	createDirectFieldProperties(IBlogViewEvent)

	__external_class_name__ = "BlogViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.blogviewevent'

@interface.implementer(INoteViewEvent)
class NoteViewEvent(RootContextEvent):
	createDirectFieldProperties(INoteViewEvent)

	__external_class_name__ = "NoteViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.noteviewevent'

@interface.implementer(ITopicViewEvent)
class TopicViewEvent(RootContextEvent):
	createDirectFieldProperties(ITopicViewEvent)

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

@interface.implementer(IUserResearchStatusEvent)
class UserResearchStatusEvent(ObjectEvent):

	def __init__(self, user, allow_research):
		super(UserResearchStatusEvent, self).__init__(user)
		self.allow_research = allow_research

	@property
	def user(self):
		return self.object

@component.adapter(IUser)
@interface.implementer(IUserResearchStatus)
class _Researchable(PersistentCreatedAndModifiedTimeObject):

	_SET_CREATED_MODTIME_ON_INIT = False
	
	lastModified = None
	allow_research = False
	
	def __init__(self):
		PersistentCreatedAndModifiedTimeObject.__init__(self)

_UserResearchStatus = an_factory( _Researchable, 'research_status' )

def delete_research_status(user):
	try:
		annotations = user.__annotations__
		annotations.pop('research_status', None)
	except AttributeError:
		pass
