#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 25.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 27

from zope.component.hooks import setHooks

from sqlalchemy import Column
from sqlalchemy import Integer

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db
from nti.analytics.database.blogs import BlogsCreated
from nti.analytics.database.blogs import BlogLikes
from nti.analytics.database.blogs import BlogFavorites
from nti.analytics.database.blogs import BlogCommentsCreated
from nti.analytics.database.blogs import BlogCommentLikes
from nti.analytics.database.blogs import BlogCommentFavorites
from nti.analytics.database.boards import ForumCommentsCreated
from nti.analytics.database.boards import ForumCommentLikes
from nti.analytics.database.boards import ForumCommentFavorites
from nti.analytics.database.boards import TopicsCreated
from nti.analytics.database.boards import TopicLikes
from nti.analytics.database.boards import TopicFavorites
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import NoteLikes
from nti.analytics.database.resource_tags import NoteFavorites

TABLES = [ ( BlogLikes, BlogsCreated, 'blog_id', BlogsCreated.blog_id ),
			( BlogFavorites, BlogsCreated, 'blog_id', BlogsCreated.blog_id ),
			( BlogCommentLikes, BlogCommentsCreated, 'comment_id', BlogCommentsCreated.comment_id ),
			( BlogCommentFavorites, BlogCommentsCreated, 'comment_id', BlogCommentsCreated.comment_id ),
			( ForumCommentLikes, ForumCommentsCreated, 'comment_id', ForumCommentsCreated.comment_id ),
			( ForumCommentFavorites, ForumCommentsCreated, 'comment_id', ForumCommentsCreated.comment_id ),
			( TopicLikes, TopicsCreated, 'topic_id', TopicsCreated.topic_id ),
			( TopicFavorites, TopicsCreated, 'topic_id', TopicsCreated.topic_id ),
			( NoteLikes, NotesCreated, 'note_id', NotesCreated.note_id ),
			( NoteFavorites, NotesCreated, 'note_id', NotesCreated.note_id ) ]

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
	for table, _, _, _ in TABLES:
		if not _column_exists( connection, table.__tablename__, 'creator_id' ):
			op.add_column( table.__tablename__, Column('creator_id', Integer, nullable=False) )

	def fetch_parent_record( table, column, parent_id ):
		result = db.session.query( table ).filter( column == parent_id ).first()
		return result

	updated = 0

	# Now populate creator id column
	for table, parent_table, column_name, parent_column in TABLES:
		logger.info( "Updating %s", table.__tablename__ )

		for record in db.session.query( table ).yield_per( 1000 ):
			updated += 1
			record_id = getattr( record, column_name )

			parent_record = fetch_parent_record( parent_table, parent_column, record_id )
			creator_id = parent_record.user_id
			record.creator_id = creator_id

	logger.info( 'Finished analytics evolve (%s) (updated_records=%s)', generation, updated )

def evolve( _ ):
	"""
	Add 'creator_id' column to denormalize likes/favorites.
	"""
	do_evolve()
