#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.annotation.factory import factory as an_factory

from zope.interface.interfaces import ObjectEvent

from nti.analytics.interfaces import VIDEO_SKIP
from nti.analytics.interfaces import VIDEO_WATCH

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IBlogViewEvent
from nti.analytics.interfaces import INoteViewEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import ITopicViewEvent
from nti.analytics.interfaces import ISurveyViewEvent
from nti.analytics.interfaces import IAnalyticsSession
from nti.analytics.interfaces import IAnalyticsSessions
from nti.analytics.interfaces import IBatchResourceEvents
from nti.analytics.interfaces import ICourseCatalogViewEvent
from nti.analytics.interfaces import IUserResearchStatus
from nti.analytics.interfaces import IUserResearchStatusEvent
from nti.analytics.interfaces import IAnalyticsClientParams
from nti.analytics.interfaces import IVideoPlaySpeedChangeEvent
from nti.analytics.interfaces import ISelfAssessmentViewEvent
from nti.analytics.interfaces import IAssignmentViewEvent
from nti.analytics.interfaces import IProfileViewEvent
from nti.analytics.interfaces import IProfileActivityViewEvent
from nti.analytics.interfaces import IProfileMembershipViewEvent
from nti.analytics.interfaces import IGeographicalLocation

from nti.dataserver.interfaces import IUser

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.externalization.persistence import NoPickle
from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

logger = __import__('logging').getLogger(__name__)


def _replace_state(obj, old, new):
	if old in obj.__dict__:
		value = obj.__dict__.pop(old)
		if obj.__dict__.get(new, None) is None:
			obj.__dict__[new] = value


@WithRepr
class ViewEvent(SchemaConfigured):

	__external_can_create__ = True
	time_length = alias('Duration')
	context_path = None # bwc

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

	resource_id = alias('ResourceId')

	__external_class_name__ = "ResourceEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.resourceevent'


@interface.implementer(ISelfAssessmentViewEvent)
class SelfAssessmentViewEvent(RootContextEvent):
	createDirectFieldProperties(ISelfAssessmentViewEvent)

	resource_id = QuestionSetId = alias('ResourceId')
	content_id = alias('ContentId')

	__external_class_name__ = "SelfAssessmentViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.selfassessmentviewevent'


@interface.implementer(IAssignmentViewEvent)
class AssignmentViewEvent(RootContextEvent):
	createDirectFieldProperties(IAssignmentViewEvent)

	resource_id = AssignmentId = alias('ResourceId')
	content_id = alias('ContentId')

	__external_class_name__ = "AssignmentViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.assignmentviewevent'


@interface.implementer(ISurveyViewEvent)
class SurveyViewEvent(RootContextEvent):
	createDirectFieldProperties(ISurveyViewEvent)

	resource_id = SurveyId = alias('ResourceId')
	content_id = alias('ContentId')

	__external_class_name__ = "SurveyViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.surveyviewevent'


@interface.implementer(IVideoEvent)
class WatchVideoEvent(RootContextEvent):
	createDirectFieldProperties(IVideoEvent)
	PlaySpeed = None # bwc

	__external_class_name__ = "WatchVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.watchvideoevent'
	event_type = VIDEO_WATCH

	course = alias('RootContextID')
	resource_id = alias('ResourceId')


@interface.implementer(IVideoEvent)
class SkipVideoEvent(RootContextEvent):
	createDirectFieldProperties(IVideoEvent)
	PlaySpeed = None # bwc

	__external_class_name__ = "SkipVideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.skipvideoevent'
	event_type = VIDEO_SKIP

	course = alias('RootContextID')
	resource_id = alias('ResourceId')


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


@interface.implementer(IVideoPlaySpeedChangeEvent)
class VideoPlaySpeedChangeEvent(SchemaConfigured):
	createDirectFieldProperties(IVideoPlaySpeedChangeEvent)

	__external_can_create__ = True
	__external_class_name__ = "VideoPlaySpeedChangeEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.videoplayspeedchange'

	resource_id = alias('ResourceId')

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)


@interface.implementer(IProfileViewEvent)
class ProfileViewEvent(ViewEvent):
	createDirectFieldProperties(IProfileViewEvent)

	__external_class_name__ = "ProfileViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.profileviewevent'


@interface.implementer(IProfileActivityViewEvent)
class ProfileActivityViewEvent(ViewEvent):
	createDirectFieldProperties(IProfileActivityViewEvent)

	__external_class_name__ = "ProfileActivityViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.profileactivityviewevent'


@interface.implementer(IProfileMembershipViewEvent)
class ProfileMembershipViewEvent(ViewEvent):
	createDirectFieldProperties(IProfileMembershipViewEvent)

	__external_class_name__ = "ProfileMembershipViewEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.profilemembershipviewevent'


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


@interface.implementer(IGeographicalLocation)
@WithRepr
class GeographicalLocation(SchemaConfigured):
	createDirectFieldProperties(IGeographicalLocation)

	__external_class_name__ = "GeographicalLocation"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.geographicallocation'

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

	def __init__(self):
		PersistentCreatedAndModifiedTimeObject.__init__(self)
		self.allow_research = False
		self.lastModified = None


_UserResearchStatus = an_factory(_Researchable, 'research_status')


def delete_research_status(user):
	try:
		annotations = user.__annotations__
		annotations.pop('research_status', None)
	except AttributeError:
		pass


@interface.implementer(IAnalyticsClientParams)
@WithRepr
class AnalyticsClientParams(SchemaConfigured):
	createDirectFieldProperties(IAnalyticsClientParams)

	__external_can_create__ = True
	__external_class_name__ = "AnalyticsClientParams"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.analyticsclientparams'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
