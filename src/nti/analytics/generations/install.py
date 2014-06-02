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

from ..async import queue
from ..async import interfaces as asyc_interfaces

class _GraphDBSchemaManager(SchemaManager):
	"""
	A schema manager that we can register as a utility in ZCML.
	"""
	def __init__(self):
		super(_GraphDBSchemaManager, self).__init__(
											generation=generation,
											minimum_generation=generation,
											package_name='nti.analytics.generations')
def evolve(context):
	# ### from IPython.core.debugger import Tracer; Tracer()()
	install_queue(context)

def install_queue(context):
	conn = context.connection
	root = conn.root()

	dataserver_folder = root['nti.dataserver']
	lsm = dataserver_folder.getSiteManager()
	intids = lsm.getUtility(zope.intid.IIntIds)

# 	result = queue.Queue()
# 	result.__parent__ = dataserver_folder
# 	##FIXME what's this
# 	result.__name__ = '++etc++graphdb++queue'
# 	intids.register(result)
# 	lsm.registerUtility(result, provided=asyc_interfaces.IQueue)
# 	
# # 	lsm.unregisterUtility( result, provided=asyc_interfaces.IQueue )

	return result
