#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 21.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 22

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Column
from sqlalchemy import String

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

def do_evolve():
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	column_name = 'play_speed'

	if not _column_exists( connection, 'VideoEvents', column_name ):
		op.add_column( 'VideoEvents', Column( column_name, String( 16 ), nullable=True ) )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve(context):
	"""
	Add play_speed column.
	"""
	do_evolve( context )
