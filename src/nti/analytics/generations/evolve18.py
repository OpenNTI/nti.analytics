#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 13.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 18

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Column
from sqlalchemy import String

from nti.analytics.database import get_analytics_db

COLUMN_EXISTS_QUERY = 	"""
						SELECT *
						FROM information_schema.COLUMNS
						WHERE TABLE_SCHEMA = 'Analytics'
							AND TABLE_NAME = '%s'
							AND COLUMN_NAME = '%s'
						"""

def _column_exists( con, table, column ):
	res = con.execute( COLUMN_EXISTS_QUERY % ( table, column ) )
	return res.scalar()

NEW_COLUMN_NAME = 'context_path'

def do_evolve():
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	for table_name in ( 'BlogsViewed', 'NotesViewed', 'TopicsViewed', 'CourseCatalogViews' ):
		if not _column_exists( connection, table_name, NEW_COLUMN_NAME ):
			op.add_column( table_name, Column( NEW_COLUMN_NAME, String( 1048 ), nullable=True ) )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve(context):
	"""
	Evolve to generation 18
	"""
	do_evolve()
