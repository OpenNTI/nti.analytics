#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 2.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 2

import zope.intid
from zope import component
from zope.component.hooks import site, setHooks

from nti.async import queue
from nti.async.interfaces import IQueue

from nti.analytics import SOCIAL_ANALYTICS
from nti.analytics import BLOGS_ANALYTICS
from nti.analytics import BOARDS_ANALYTICS
from nti.analytics import ASSESSMENTS_ANALYTICS
from nti.analytics import ENROLL_ANALYTICS
from nti.analytics import TAGS_ANALYTICS
from nti.analytics import RESOURCE_VIEW_ANALYTICS
from nti.analytics import VIDEO_VIEW_ANALYTICS
from nti.analytics import CATALOG_VIEW_ANALYTICS
from nti.analytics import TOPIC_VIEW_ANALYTICS
from nti.analytics import NOTE_VIEW_ANALYTICS
from nti.analytics import BLOG_VIEW_ANALYTICS
from nti.analytics import SESSIONS_ANALYTICS
from nti.analytics import DELETE_ANALYTICS

from nti.analytics import QUEUE_NAME as LEGACY_QUEUE_NAME

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

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		lsm = ds_folder.getSiteManager()
		old_queue = component.queryUtility( IQueue, name=LEGACY_QUEUE_NAME )
		intids = lsm.getUtility(zope.intid.IIntIds)

		# Out with the old
		# <Manually removed in alpha>
		if old_queue is not None:
			lsm.unregisterUtility( old_queue, provided=IQueue )
			intids.unregister( old_queue )

		for new_queue_name in QUEUE_NAMES:
			result = queue.Queue()
			result.__parent__ = ds_folder
			result.__name__ = new_queue_name
			intids.register( result )
			lsm.registerUtility( result, provided=IQueue, name=new_queue_name )

	logger.info( 'Finished analytics evolve2' )

def evolve(context):
	"""
	Evolve to generation 2
	"""
	do_evolve(context)
