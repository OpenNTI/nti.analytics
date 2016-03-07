#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 40

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import inspect

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from nti.analytics.generations._utils import do_evolve
from nti.analytics.generations._utils import mysql_foreign_key_exists

TABLES = ['NotesCreated',
	      'BlogCommentsCreated',
	      'ForumCommentsCreated']

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
	users_table = 'Users'
	column_id = 'parent_user_id'
	ref_column_id = 'user_id'

	for table in TABLES:
		if not mysql_foreign_key_exists( connection, schema, table, column_id, users_table ):
			op.create_foreign_key( 'fk_' + table + '_parent_user',
									table,
									users_table,
									[column_id], [ref_column_id] )
			logger.info( 'Creating foreign key for table (%s) (%s)', table, schema )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Add resource foreign key for parent_user_id.
	"""
	do_evolve( context, evolve_job, generation )
