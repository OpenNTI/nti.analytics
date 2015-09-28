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

from nti.externalization.interfaces import IInternalObjectUpdater
from nti.externalization.datastructures import InterfaceObjectIO

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import ICourseCatalogViewEvent
from nti.analytics.interfaces import IBlogViewEvent
from nti.analytics.interfaces import INoteViewEvent
from nti.analytics.interfaces import ITopicViewEvent
from nti.analytics.interfaces import IAnalyticsSession
from nti.analytics.interfaces import IProfileViewEvent
from nti.analytics.interfaces import IAssignmentViewEvent
from nti.analytics.interfaces import ISelfAssessmentViewEvent
from nti.analytics.interfaces import IProfileActivityViewEvent
from nti.analytics.interfaces import IProfileMembershipViewEvent

@interface.implementer(IInternalObjectUpdater)
class _NTIAnalyticsModelUpdater(object):

	model_interface = None

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		root_context_id = parsed.get('course', None)
		duration = parsed.get('time_length', None)
		resource_id = parsed.get('resource_id', None)
		if root_context_id is not None and parsed.get('RootContextID') is None:
			parsed['RootContextID'] = root_context_id
		if duration is not None and parsed.get('Duration') is None:
			parsed['Duration'] = duration
		if resource_id is not None and parsed.get('ResourceId') is None:
			parsed['ResourceId'] = resource_id
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
