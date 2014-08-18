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

from nti.analytics import QUEUE_NAMES
from nti.analytics import QUEUE_NAME as LEGACY_QUEUE_NAME

def do_evolve(context, reg_intid=True):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		lsm = ds_folder.getSiteManager()
		old_queue = component.getUtility( IQueue, name=LEGACY_QUEUE_NAME )
		intids = lsm.getUtility(zope.intid.IIntIds)

		# Out with the old
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
	Evolve to generation 2 by adding all objects to index queue
	"""
	do_evolve(context)
