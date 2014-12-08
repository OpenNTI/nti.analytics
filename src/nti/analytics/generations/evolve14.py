#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 14.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 14

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db

INDEX_EXISTS_QUERY = 	"""
						SHOW INDEX FROM Analytics.%s
						WHERE KEY_NAME = '%s';
						"""

def _index_exists( con, ix_name, table ):
	res = con.execute( INDEX_EXISTS_QUERY % ( table, ix_name ) )
	return res.scalar()

def do_evolve():
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)
	ix_name = 'ix_resources_resource_ds_id'

	if not _index_exists( connection, ix_name, 'Resources' ):
		op.create_index( ix_name, "Resources", ['resource_ds_id'] )

	logger.info( 'Finished analytics evolve14' )

def evolve(context):
	"""
	Evolve to generation 14
	"""
	do_evolve()
