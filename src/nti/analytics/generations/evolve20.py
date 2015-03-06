#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 20.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 20

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy.engine.reflection import Inspector

from nti.analytics.database import get_analytics_db

def _table_exists( inspector, table ):
	return table in inspector.get_table_names()

def do_evolve():
	setHooks()

	db = get_analytics_db()
	inspector = Inspector.from_engine( db.engine )

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	table_name = 'CurrentSessions'

	if _table_exists( inspector, table_name ):
		op.drop_table( table_name )

	logger.info( 'Finished analytics evolve %s', generation )

def evolve(context):
	"""
	Drop the CurrentSessions table.
	"""
	do_evolve()
