#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import logging

from zope import component
from zc.blist import BList

from .interfaces import IAnalyticsQueueFactory

QUEUE_NAME = '++etc++analytics++queue'

SOCIAL_ANALYTICS = QUEUE_NAME + '++social'
BLOGS_ANALYTICS = QUEUE_NAME + '++blog'
BOARDS_ANALYTICS = QUEUE_NAME + '++boards'
TOPICS_ANALYTICS = QUEUE_NAME + '++topics'
COMMENTS_ANALYTICS = QUEUE_NAME + '++comments'
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

# Order is important here.  We happen to know that
# nti.async processes these queues in order.  The boards (and blogs)
# must come before the topics must come before the comments.
# This implementation detail is only relevant at migration time.
QUEUE_NAMES = [ SOCIAL_ANALYTICS,
				ASSESSMENTS_ANALYTICS,
				BLOGS_ANALYTICS,
				BOARDS_ANALYTICS,
				ENROLL_ANALYTICS,
				TAGS_ANALYTICS,
				TOPICS_ANALYTICS,
				COMMENTS_ANALYTICS,
				RESOURCE_VIEW_ANALYTICS,
				VIDEO_VIEW_ANALYTICS,
				CATALOG_VIEW_ANALYTICS,
				TOPIC_VIEW_ANALYTICS,
				NOTE_VIEW_ANALYTICS,
				BLOG_VIEW_ANALYTICS,
				SESSIONS_ANALYTICS,
				DELETE_ANALYTICS ]

def get_factory():
	return component.getUtility(IAnalyticsQueueFactory)
