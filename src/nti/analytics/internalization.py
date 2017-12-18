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

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectUpdater

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import IBlogViewEvent
from nti.analytics.interfaces import INoteViewEvent
from nti.analytics.interfaces import ITopicViewEvent
from nti.analytics.interfaces import IAnalyticsSession
from nti.analytics.interfaces import IProfileViewEvent
from nti.analytics.interfaces import IAssignmentViewEvent
from nti.analytics.interfaces import ICourseCatalogViewEvent
from nti.analytics.interfaces import ISelfAssessmentViewEvent
from nti.analytics.interfaces import IProfileActivityViewEvent
from nti.analytics.interfaces import IProfileMembershipViewEvent

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IInternalObjectUpdater)
class _NTIAnalyticsModelUpdater(object):

	model_interface = None

	def __init__(self, obj):
		self.obj = obj

	field_map = { 'course': 'RootContextID',
				  'time_length': 'Duration',
				  'timelength': 'Duration',
				  'resource_id': 'ResourceId',
				  'topic_id': 'blog_id' }

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		for old, new in self.field_map.items():
			old_val = parsed.get( old )
			if old_val is not None and parsed.get( new ) is None:
				parsed[new] = old_val
		result = InterfaceObjectIO(self.obj, self.model_interface).updateFromExternalObject(parsed)
		return result


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IVideoEvent)
class _VideoEventUpdater(_NTIAnalyticsModelUpdater):

	model_interface = IVideoEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IResourceEvent)
class _ResourceEventUpdater(_NTIAnalyticsModelUpdater):

	model_interface = IResourceEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(ICourseCatalogViewEvent)
class _CourseCatalogEventUpdater(_NTIAnalyticsModelUpdater):

	model_interface = ICourseCatalogViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IBlogViewEvent)
class _BlogViewEventUpdater(_NTIAnalyticsModelUpdater):

	model_interface = IBlogViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(INoteViewEvent)
class _NoteViewEventUpdater(_NTIAnalyticsModelUpdater):

	model_interface = INoteViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(ITopicViewEvent)
class _TopicViewEventUpdater(_NTIAnalyticsModelUpdater):

	model_interface = ITopicViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IAnalyticsSession)
class _AnalyticsSessionUpdater(_NTIAnalyticsModelUpdater):

	model_interface = IAnalyticsSession


# TODO Why do we need distinct updaters since we implement
# the same base class?


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IProfileViewEvent)
class _ProfileViewEvent(_NTIAnalyticsModelUpdater):

	model_interface = IProfileViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IProfileActivityViewEvent)
class _ProfileActivityViewEvent(_NTIAnalyticsModelUpdater):

	model_interface = IProfileActivityViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IProfileMembershipViewEvent)
class _ProfileMembershipViewEvent(_NTIAnalyticsModelUpdater):

	model_interface = IProfileMembershipViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(IAssignmentViewEvent)
class _AssignmentViewEvent(_NTIAnalyticsModelUpdater):

	model_interface = IAssignmentViewEvent


@interface.implementer(IInternalObjectUpdater)
@component.adapter(ISelfAssessmentViewEvent)
class _SelfAssessmentViewEvent(_NTIAnalyticsModelUpdater):

	model_interface = ISelfAssessmentViewEvent

