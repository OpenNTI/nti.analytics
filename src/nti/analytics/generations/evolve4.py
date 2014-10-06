#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 4.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid
from zope import component
from zope.component.hooks import site, setHooks

from nti.async.interfaces import IQueue

generation = 4

QUEUE_NAME = '++etc++analytics++queue'

SOCIAL_ANALYTICS = QUEUE_NAME + '++social'
BLOGS_ANALYTICS = QUEUE_NAME + '++blog'
BOARDS_ANALYTICS = QUEUE_NAME + '++boards'
TOPICS_ANALYTICS = QUEUE_NAME + '++topics'
COMMENTS_ANALYTICS = QUEUE_NAME + '++comments'
ASSESSMENTS_ANALYTICS = QUEUE_NAME + '++assessments'
ENROLL_ANALYTICS = QUEUE_NAME + '++enroll'
TAGS_ANALYTICS = QUEUE_NAME + '++tags'
RESOURCE_VIEW_ANALYTICS = QUEUE_NAME + '++resource++views'
VIDEO_VIEW_ANALYTICS = QUEUE_NAME + '++video++views'
CATALOG_VIEW_ANALYTICS = QUEUE_NAME + '++catalog++views'
TOPIC_VIEW_ANALYTICS = QUEUE_NAME + '++topic++views'
BLOG_VIEW_ANALYTICS = QUEUE_NAME + '++blog++views'
NOTE_VIEW_ANALYTICS = QUEUE_NAME + '++note++views'
SESSIONS_ANALYTICS = QUEUE_NAME + '++sessions'
DELETE_ANALYTICS = QUEUE_NAME + '++delete'
FAIL_QUEUE = QUEUE_NAME + '++failure'

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
				DELETE_ANALYTICS,
				FAIL_QUEUE ]

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		lsm = ds_folder.getSiteManager()

		for queue_name in QUEUE_NAMES:
			old_queue = component.queryUtility( IQueue, name=queue_name )
			intids = lsm.getUtility(zope.intid.IIntIds)

			# Out with the old
			if old_queue is not None:
				lsm.unregisterUtility( old_queue, provided=IQueue )
				intids.unregister( old_queue )

	logger.info( 'Finished analytics evolve4' )

def evolve(context):
	"""
	Evolve to generation 4
	"""
	do_evolve(context)
