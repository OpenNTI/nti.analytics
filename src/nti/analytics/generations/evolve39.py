#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 39.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 39

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import inspect

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from ._utils import do_evolve
from ._utils import mysql_foreign_key_exists

TABLES = ['AssignmentViews',
	      'SelfAssessmentViews']

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)
	inspector = inspect( db.engine )
	schema = inspector.default_schema_name
	resource_table = 'Resources'
	column_id = 'resource_id'

	for table in TABLES:
		if not mysql_foreign_key_exists( connection, schema, table, column_id, resource_table ):
			op.create_foreign_key( 'fk_' + table + '_resources',
									table,
									resource_table,
									[column_id], [column_id] )
			logger.info( 'Creating foreign key for table (%s) (%s)', table, schema )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Add resource foreign key for assessment view tables.
	"""
	do_evolve( context, evolve_job, generation )
