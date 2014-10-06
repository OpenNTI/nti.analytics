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

@interface.implementer(IInternalObjectUpdater)
class _NTIAnalyticsModelUpdater(object):

	model_interface = None

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		root_context_id = parsed.get('course', None)
		duration = parsed.get('time_length', None)
		if root_context_id is not None and parsed.get('RootContextID') is None:
			parsed['RootContextID'] = root_context_id
		if duration is not None and parsed.get('Duration') is None:
			parsed['Duration'] = duration
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
