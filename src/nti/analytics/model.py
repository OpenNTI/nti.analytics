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
from nti.externalization.externalization import WithRepr

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.analytics import interfaces

@interface.implementer(interfaces.IResourceEvent)
@WithRepr
@NoPickle
class ResourceEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.IResourceEvent)

	__external_can_create__ = True
	__external_class_name__ = "ResourceEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.resourceevent'

@interface.implementer(interfaces.IVideoEvent)
@WithRepr
@NoPickle
class VideoEvent(SchemaConfigured):
	createDirectFieldProperties(interfaces.IVideoEvent)

	__external_can_create__ = True
	__external_class_name__ = "VideoEvent"
	mime_type = mimeType = 'application/vnd.nextthought.analytics.videoevent'

