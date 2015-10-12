#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.analytics')

from zope import component

from zope.security.interfaces import NoInteraction
from zope.security.management import getInteraction
from zope.security.management import queryInteraction

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser

from nti.analytics.database import get_analytics_db

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

# This one perhaps needs more buckets
RESOURCE_VIEW_ANALYTICS = QUEUE_NAME + '++resource++views'
VIDEO_VIEW_ANALYTICS = QUEUE_NAME + '++video++views'
CATALOG_VIEW_ANALYTICS = QUEUE_NAME + '++catalog++views'
TOPIC_VIEW_ANALYTICS = QUEUE_NAME + '++topic++views'
BLOG_VIEW_ANALYTICS = QUEUE_NAME + '++blog++views'
NOTE_VIEW_ANALYTICS = QUEUE_NAME + '++note++views'

SESSIONS_ANALYTICS = QUEUE_NAME + '++sessions'
DELETE_ANALYTICS = QUEUE_NAME + '++delete'
USERS_ANALYTICS = QUEUE_NAME + '++users'

# Order is important here.  We happen to know that
# nti.async processes these queues in order.  The boards (and blogs)
# must come before the topics must come before the comments.
# This implementation detail is only relevant at migration time,
# or when multiple processes are running.
# -> Since we now are idempotent and can lazy create
# 	 parent objects in most cases, this is no longer strictly necessary.
QUEUE_NAMES = [ SESSIONS_ANALYTICS,
				SOCIAL_ANALYTICS,
				ASSESSMENTS_ANALYTICS,
				BLOGS_ANALYTICS,
				BOARDS_ANALYTICS,
				ENROLL_ANALYTICS,
				TAGS_ANALYTICS,
				TOPICS_ANALYTICS,
				COMMENTS_ANALYTICS,
				USERS_ANALYTICS,
				RESOURCE_VIEW_ANALYTICS,
				VIDEO_VIEW_ANALYTICS,
				CATALOG_VIEW_ANALYTICS,
				TOPIC_VIEW_ANALYTICS,
				NOTE_VIEW_ANALYTICS,
				BLOG_VIEW_ANALYTICS,
				DELETE_ANALYTICS ]

def has_analytics():
	"Determines whether our current site is configured for analytics."
	return get_analytics_db(strict=False) is not None

def get_factory():
	return component.getUtility(IAnalyticsQueueFactory)

def get_current_username():
	try:
		return getInteraction().participations[0].principal.id
	except (NoInteraction, IndexError, AttributeError):
		return None

def get_current_user(user=None):
	user = get_current_username() if user is None else user
	if user is not None and not IUser.providedBy(user):
		user = User.get_user(str(user))
	return user
