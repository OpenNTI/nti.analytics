#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 12.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 12

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Interval

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

def do_evolve():
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	if not _column_exists( connection, 'Courses', 'start_date' ):
		op.add_column( "Courses", Column('start_date', DateTime, nullable=True) )

	if not _column_exists( connection, 'Courses', 'end_date' ):
		op.add_column( "Courses", Column('end_date', DateTime, nullable=True) )

	if not _column_exists( connection, 'Courses', 'duration' ):
		op.add_column( "Courses", Column('duration', Interval, nullable=True) )

	if not _column_exists( connection, 'Users', 'create_date' ):
		op.add_column( "Users", Column('create_date', DateTime, nullable=True) )

	logger.info( 'Finished analytics evolve12' )

def evolve(context):
	"""
	Evolve to generation 12
	"""
	do_evolve()
