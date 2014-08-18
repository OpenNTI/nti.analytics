#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
analytics module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import logging

from zope import component
from zc.blist import BList

from nti.dataserver import interfaces as nti_interfaces

from nti.analytics.interfaces import IAnalyticsQueueFactory

QUEUE_NAME = '++etc++analytics++queue'

SOCIAL_ANALYTICS = QUEUE_NAME + '++social'
BLOGS_ANALYTICS = QUEUE_NAME + '++blog'
BOARDS_ANALYTICS = QUEUE_NAME + '++boards'
ASSESSMENTS_ANALYTICS = QUEUE_NAME + '++assessments'
ENROLL_ANALYTICS = QUEUE_NAME + '++enroll'
TAGS_ANALYTICS = QUEUE_NAME + '++tags'
# This one needs more buckets
RESOURCE_VIEW_ANALYTICS = QUEUE_NAME + '++resource++views'
VIDEO_VIEW_ANALYTICS = QUEUE_NAME + '++video++views'
CATALOG_VIEW_ANALYTICS = QUEUE_NAME + '++catalog++views'
TOPIC_VIEW_ANALYTICS = QUEUE_NAME + '++topic++views'
BLOG_VIEW_ANALYTICS = QUEUE_NAME + '++blog++views'
NOTE_VIEW_ANALYTICS = QUEUE_NAME + '++note++views'

SESSIONS_ANALYTICS = QUEUE_NAME + '++sessions'
DELETE_ANALYTICS = QUEUE_NAME + '++delete'

QUEUE_NAMES = [ SOCIAL_ANALYTICS,
				BLOGS_ANALYTICS,
				BOARDS_ANALYTICS,
				ASSESSMENTS_ANALYTICS,
				ENROLL_ANALYTICS,
				TAGS_ANALYTICS,
				RESOURCE_VIEW_ANALYTICS,
				VIDEO_VIEW_ANALYTICS,
				CATALOG_VIEW_ANALYTICS,
				TOPIC_VIEW_ANALYTICS,
				NOTE_VIEW_ANALYTICS,
				BLOG_VIEW_ANALYTICS,
				SESSIONS_ANALYTICS,
				DELETE_ANALYTICS ]

def get_factory():
	return component.getUtility( IAnalyticsQueueFactory )
