#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 31.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 31

from zope.component.hooks import setHooks

from sqlalchemy import Column
from sqlalchemy import Integer

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db

from ._utils import do_evolve
from ._utils import mysql_column_exists

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		# Even with batch_op, sqlite has issues
		# Index name constraint: perhaps on copying the table?
		# Either way, alembic currently doesn't handle that.
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	if mysql_column_exists( connection, 'VideoEvents', 'max_time_length' ):
		op.drop_column( 'VideoEvents', 'max_time_length' )

	if not mysql_column_exists( connection, 'Resources', 'max_time_length' ):
		op.add_column( 'Resources', Column( 'max_time_length', Integer, nullable=True ) )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Move our max_time_length column from VideoEvents to Resources.
	We're losing data, but we'll re-populate later.
	"""
	do_evolve( context, evolve_job, generation )
