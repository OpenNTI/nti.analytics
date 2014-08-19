# -*- coding: utf-8 -*-
"""
schema generation installation.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 3

from zope.generations.generations import SchemaManager

import zope.intid

from nti.async import queue
from nti.async.interfaces import IQueue

from nti.analytics import QUEUE_NAMES
from nti.analytics import FAIL_QUEUE

class _AnalyticsSchemaManager(SchemaManager):
	"""
	A schema manager that we can register as a utility in ZCML.
	"""
	def __init__(self):
		super(_AnalyticsSchemaManager, self).__init__(
											generation=generation,
											minimum_generation=generation,
											package_name='nti.analytics.generations')
def evolve(context):
	install_queue(context)

def install_queue(context):
	conn = context.connection
	root = conn.root()

	ds_folder = root['nti.dataserver']
	lsm = ds_folder.getSiteManager()
	intids = lsm.getUtility(zope.intid.IIntIds)

	queue_names = QUEUE_NAMES + [FAIL_QUEUE]

	for new_queue_name in queue_names:
		result = queue.Queue()
		result.__parent__ = ds_folder
		result.__name__ = new_queue_name
		intids.register( result )
		lsm.registerUtility( result, provided=IQueue, name=new_queue_name )

