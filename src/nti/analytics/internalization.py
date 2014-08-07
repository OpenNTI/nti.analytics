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

@interface.implementer(IInternalObjectUpdater)
@component.adapter(IVideoEvent)
class _VideoEventUpdater(object):

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		result = InterfaceObjectIO( self.obj, IVideoEvent ).updateFromExternalObject(parsed)
		return result

@interface.implementer(IInternalObjectUpdater)
@component.adapter(IResourceEvent)
class _ResourceEventUpdater(object):

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		result = InterfaceObjectIO( self.obj, IResourceEvent ).updateFromExternalObject( parsed )
		return result

@interface.implementer(IInternalObjectUpdater)
@component.adapter(ICourseCatalogViewEvent)
class _CourseCatalogEventUpdater(object):

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		result = InterfaceObjectIO( self.obj, ICourseCatalogViewEvent ).updateFromExternalObject( parsed )
		return result
