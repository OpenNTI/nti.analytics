# -*- coding: utf-8 -*-
"""
schema generation installation.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 1

from zope.generations.generations import SchemaManager

import zope.intid

from nti.async import queue
from nti.async import interfaces as asyc_interfaces

from .. import QUEUE_NAME

class _AnalyticsDBSchemaManager(SchemaManager):
	"""
	A schema manager that we can register as a utility in ZCML.
	"""
	def __init__(self):
		super(_AnalyticsDBSchemaManager, self).__init__(
											generation=generation,
											minimum_generation=generation,
											package_name='nti.analytics.generations')
def evolve(context):
	install_queue(context)

def install_queue(context):
	conn = context.connection
	root = conn.root()

	dataserver_folder = root['nti.dataserver']
	lsm = dataserver_folder.getSiteManager()
	intids = lsm.getUtility(zope.intid.IIntIds)

	result = queue.Queue()
	result.__parent__ = dataserver_folder
	result.__name__ = QUEUE_NAME
	intids.register( result )
	lsm.registerUtility( result, provided=asyc_interfaces.IQueue, name=QUEUE_NAME )
# 	lsm.unregisterUtility( result, provided=asyc_interfaces.IQueue )

	return result
