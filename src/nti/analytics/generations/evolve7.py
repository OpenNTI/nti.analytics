#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 6.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 7

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Integer

from nti.analytics.database import get_analytics_db

INSERT_SQL ="""
			INSERT INTO Resources
			( resource_ds_id )
			SELECT DISTINCT resource_id
			FROM CourseResourceViews
			UNION
			SELECT DISTINCT resource_id
			From VideoEvents
			UNION
			SELECT DISTINCT resource_id
			FROM NotesCreated
			UNION
			SELECT DISTINCT resource_id
			FROM NotesViewed
			UNION
			SELECT DISTINCT resource_id
			FROM HighlightsCreated;
			"""

UPDATE_SQL = """UPDATE %s old_table
				INNER JOIN Resources new_table
					ON old_table.resource_id = new_table.resource_ds_id
				SET old_table.resource_id = new_table.resource_id;
			"""

OLD_TABLES = ['CourseResourceViews', 'VideoEvents', 'NotesCreated', 'NotesViewed', 'HighlightsCreated']

def do_evolve(context):
	setHooks()

	# This should automatically build our new resources table
	db = get_analytics_db()
	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	# We cannot use our transaction connection since we have
	# implicit commits below.
	connection = db.engine.connect()

	# Fill our new table
	logger.info( 'Populating new table' )
	connection.execute( INSERT_SQL )
	db.session.flush()

	# Update our references with int vals in a string column
	logger.info( 'Update references' )
	for old_table in OLD_TABLES:
		connection.execute( UPDATE_SQL % old_table )

	mc = MigrationContext.configure( connection )
	op = Operations( mc )

	# Change our column type
	logger.info( 'Updating metadata' )
	for old_table in OLD_TABLES:
		op.alter_column( old_table, 'resource_id', type_=Integer )

	# Add foreign key constraints
	for old_table in OLD_TABLES:
		op.create_foreign_key( 'fk_' + old_table + '_resources',
								old_table,
								'Resources',
								['resource_id'], ['resource_id'] )

	logger.info( 'Finished analytics evolve7' )

def evolve(context):
	"""
	Evolve to generation 7
	"""
	do_evolve(context)
