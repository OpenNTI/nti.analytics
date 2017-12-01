#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 5.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid
from zope import component
from zope.component.hooks import site, setHooks

from nti.asynchronous.interfaces import IQueue

generation = 5

QUEUE_NAME = '++etc++analytics++queue'
FAIL_QUEUE = QUEUE_NAME + '++failure'

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		lsm = ds_folder.getSiteManager()

		old_queue = component.queryUtility( IQueue, name=FAIL_QUEUE )
		intids = lsm.getUtility(zope.intid.IIntIds)

		# Out with the old
		if old_queue is not None:
			lsm.unregisterUtility( old_queue, provided=IQueue )
			intids.unregister( old_queue )

	logger.info( 'Finished analytics evolve5' )

def evolve(context):
	"""
	Evolve to generation 5
	"""
	do_evolve(context)
