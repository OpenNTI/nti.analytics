#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 25.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 25

from zope.component.hooks import setHooks

from sqlalchemy import Column
from sqlalchemy import Integer

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db
from nti.analytics.database.blogs import BlogCommentsCreated
from nti.analytics.database.boards import ForumCommentsCreated
from nti.analytics.database.resource_tags import NotesCreated

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

	# Add our column
	for table in (BlogCommentsCreated,ForumCommentsCreated,NotesCreated):
		if not _column_exists( connection, table.__tablename__, 'parent_user_id' ):
			op.add_column( table.__tablename__, Column('parent_user_id', Integer, nullable=True) )

	def fetch_parent_record( table, column, parent_id ):
		result = db.session.query( table ).filter( column == parent_id ).first()
		return result

	updated = 0

	# Now populate parent user id column
	for table, column_name, column in (	(BlogCommentsCreated, 'comment_id', BlogCommentsCreated.comment_id),
										(ForumCommentsCreated, 'comment_id', ForumCommentsCreated.comment_id ),
										(NotesCreated, 'note_id', NotesCreated.note_id )):
		logger.info( "Updating %s", table.__tablename__ )
		parent_id_user_id_dict = {}

		for record in db.session.query( table ).yield_per( 1000 ):
			record_id = getattr( record, column_name )
			# Insert ourselves for easier lookup
			parent_id_user_id_dict[ record_id ] = record.user_id

			if record.parent_id is not None:
				# Try to find our parent user_id
				parent_user_id = None
				parent_id = record.parent_id
				if parent_id in parent_id_user_id_dict:
					parent_user_id = parent_id_user_id_dict.get( parent_id )
				else:
					parent_record = fetch_parent_record( table, column, parent_id )
					if parent_record is not None:
						parent_user_id = parent_record.user_id
						parent_id_user_id_dict[ parent_id ] = parent_user_id

				# Some forum comment ds ids do not exist for some reason.
				if parent_user_id:
					updated += 1
					# Finally, update our parent user id column
					record.parent_user_id = parent_user_id

	logger.info( 'Finished analytics evolve (%s) (updated_records=%s)', generation, updated )

def evolve(context):
	"""
	Add 'parent_user_id' column to replyTo records, with data.
	"""
	do_evolve()
