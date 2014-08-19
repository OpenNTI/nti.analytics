#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 2.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 3

import zope.intid
from zope import component
from zope.component.hooks import site, setHooks

from nti.async import queue
from nti.async.interfaces import IQueue

from nti.analytics import FAIL_QUEUE
from nti.analytics import TOPICS_ANALYTICS
from nti.analytics import COMMENTS_ANALYTICS

QUEUE_NAMES = [ FAIL_QUEUE, TOPICS_ANALYTICS, COMMENTS_ANALYTICS ]

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		lsm = ds_folder.getSiteManager()
		intids = lsm.getUtility(zope.intid.IIntIds)

		for new_queue_name in QUEUE_NAMES:
			result = queue.Queue()
			result.__parent__ = ds_folder
			result.__name__ = new_queue_name
			intids.register( result )
			lsm.registerUtility( result, provided=IQueue, name=new_queue_name )

	logger.info( 'Finished analytics evolve3' )

def evolve(context):
	"""
	Evolve to generation 3
	"""
	do_evolve(context)
