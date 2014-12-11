#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 15.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 15

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Integer
from sqlalchemy import BigInteger
from sqlalchemy import String
from sqlalchemy.exc import DatabaseError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine.reflection import Inspector

from nti.analytics.database import get_analytics_db

def _table_exists( inspector, table ):
	return table in inspector.get_table_names()

def _get_column_names( column_infos ):
	return [x['name'] for x in column_infos]

def _column_exists( inspector, table, column ):
	return column in _get_column_names( inspector.get_columns( table ) )

def _drop_index( op, table, column_name ):
	try:
		op.drop_index( 'ix_%s_%s' % ( table, column_name ), table_name=table )
	except DatabaseError:
		# Already dropped
		pass

def _add_index( op, table, column_name ):
	try:
		op.create_index( 'ix_%s_%s' % ( table, column_name ), table, [column_name] )
	except DatabaseError:
		# Already added
		pass

def _rename_column( op, table, old_name, new_name, col_type, **kwargs ):
	# Unfortunately, sqlite does not support easy column renaming.
	with op.batch_alter_table( table ) as batch_op:
		batch_op.alter_column( old_name, new_column_name=new_name, type_=col_type, **kwargs )

def do_evolve():
	setHooks()

	db = get_analytics_db()
	inspector = Inspector.from_engine( db.engine )

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	table_name = 'Courses'

	# Have to set the start autoincrement the hard way with mysql
	if db.engine.name == 'mysql':
		connection.execute( 'ALTER TABLE ContextId AUTO_INCREMENT = 1000;' )

	# And the other hard way with sqlite
	if db.engine.name == 'sqlite':
		try:
			connection.execute( 'INSERT INTO ContextId (context_id) VALUES (1000);' )
		except IntegrityError:
			pass

	# Drop our old indexes
	for old_column_name in [ 'course_id', 'course_ds_id', 'course_name' ]:
		_drop_index( op, table_name, old_column_name )

	# Rename columns
	if not _column_exists( inspector, table_name, 'context_id' ):
		# Removing autoincrement since we have new table identifier
		_rename_column( op, table_name, 'course_id', 'context_id', Integer, autoincrement=False )

	if not _column_exists( inspector, table_name, 'context_ds_id' ):
		# Changing type to NTIID instead of ds_intid
		_rename_column( op, table_name, 'course_ds_id', 'context_ds_id', String(256), existing_type=BigInteger)

	if not _column_exists( inspector, table_name, 'context_name' ):
		_rename_column( op, table_name, 'course_name', 'context_name', String(64) )

	if not _column_exists( inspector, table_name, 'context_long_name' ):
		_rename_column( op, table_name, 'course_long_name', 'context_long_name', String(256) )

	# Recreate indexes
	for new_column_name in [ 'context_id', 'context_ds_id', 'context_name' ]:
		_add_index( op, table_name, new_column_name )

	logger.info( 'Finished analytics evolve15' )

def evolve(context):
	"""
	To handle books, add a new Books table. Rename four columns
	in the Courses table to reflect this change.
	"""
	do_evolve()
