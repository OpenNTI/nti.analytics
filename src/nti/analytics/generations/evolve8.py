#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 8.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 8

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db
from nti.analytics.database.resources import Resources

def _remove_invalid_records( db ):
	# Remove all int values from Resources table due to
	# previous migration.
# 	all_resources = db.session.query( Resources ).all()
# 	delete_count = 0
# 	total_count = len( all_resources )
#
# 	for resource_record in all_resources:
# 		resource_ds_id = resource_record.resource_ds_id
# 		try:
# 			int( resource_ds_id )
# 			db.session.delete( resource_record )
# 			delete_count += 1
# 		except ValueError:
# 			# Good record
# 			pass
#
# 	logger.info( 'Finished analytics evolve8 (total=%s) (dropped_records=%s)',
# 				total_count, delete_count )
	pass

def do_evolve(context):
	setHooks()

	db = get_analytics_db()
	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	_remove_invalid_records( db )


def evolve(context):
	"""
	Evolve to generation 8
	"""
	do_evolve(context)
