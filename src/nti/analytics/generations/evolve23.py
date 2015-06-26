#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 23.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 23

from functools import partial

import zope.intid
from zope import component
from zope.component.hooks import site, setHooks
from zope.component.hooks import getSite

from sqlalchemy import Column
from sqlalchemy import Boolean
from sqlalchemy import Integer

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.dataserver.liking import LIKE_CAT_NAME
from nti.dataserver.liking import FAVR_CAT_NAME
from nti.dataserver.rating import lookup_rating_for_read

from nti.analytics.database import get_analytics_db
from nti.analytics.database import NTIID_COLUMN_TYPE

from nti.analytics.database.assessments import AssignmentViews
from nti.analytics.database.assessments import SelfAssessmentViews

from nti.analytics.database.boards import TopicLikes
from nti.analytics.database.boards import TopicFavorites
from nti.analytics.database.boards import TopicsCreated
from nti.analytics.database.boards import ForumCommentsCreated
from nti.analytics.database.boards import ForumCommentLikes
from nti.analytics.database.boards import ForumCommentFavorites
from nti.analytics.database.boards import _create_topic_rating_record
from nti.analytics.database.boards import _create_forum_comment_rating_record

from nti.analytics.database.blogs import BlogsCreated
from nti.analytics.database.blogs import BlogCommentsCreated
from nti.analytics.database.blogs import BlogLikes
from nti.analytics.database.blogs import BlogFavorites
from nti.analytics.database.blogs import BlogCommentLikes
from nti.analytics.database.blogs import BlogCommentFavorites
from nti.analytics.database.blogs import _create_blog_rating_record
from nti.analytics.database.blogs import _create_blog_comment_rating_record

from nti.analytics.database.resource_tags import NoteLikes
from nti.analytics.database.resource_tags import NoteFavorites
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import _create_note_rating_record

from nti.site.hostpolicy import run_job_in_all_host_sites

def _get_ratings( obj, rating_name ):
	return lookup_rating_for_read( obj, rating_name, safe=True )

def _get_rating_usernames( obj, rating_name ):
	ratings = _get_ratings( obj, rating_name )
	result = ()
	if ratings is not None:
		storage = ratings.storage
		result = tuple( storage.all_raters )
	return result

def _get_like_usernames( obj ):
	return _get_rating_usernames( obj, LIKE_CAT_NAME )

def _get_fave_usernames( obj ):
	return _get_rating_usernames( obj, FAVR_CAT_NAME )

def _create_rating_record( db, record, ds_id, obj_id, intids, users, fave_table, like_table, create_call ):
	# The create_call should avoid not creating duplicate records.
	# Object was deleted
	if ds_id is None:
		return 0, 0, 0

	obj = intids.queryObject( int( ds_id ) )

	timestamp = session_id = None
	delta = 1
	missing_count = 0

	if record.favorite_count > 0:
		fave_usernames = _get_fave_usernames( obj )
		for username in fave_usernames:
			user = users.get( username )
			if user is None:
				missing_count +=1
				continue
			create_call( db, fave_table, user,
						timestamp, session_id, obj_id, delta )

	if record.like_count > 0:
		like_usernames = _get_like_usernames( obj )
		for username in like_usernames:
			user = users.get( username )
			if user is None:
				missing_count += 1
				continue
			create_call( db, like_table, user,
						timestamp, session_id, obj_id, delta )

	return record.favorite_count or 0, record.like_count or 0, missing_count

def _update_forum_comments( db, record, intids, users ):
	return _create_rating_record( db, record,
						record.comment_id, record.comment_id, intids, users,
						ForumCommentFavorites,
						ForumCommentLikes,
						 _create_forum_comment_rating_record )

def _update_blogs( db, record, intids, users ):
	return _create_rating_record( db, record,
						record.blog_ds_id, record.blog_id, intids, users,
						BlogFavorites,
						BlogLikes,
						 _create_blog_rating_record )

def _update_blog_comments( db, record, intids, users ):
	return _create_rating_record( db, record,
						record.comment_id, record.comment_id, intids, users,
						BlogCommentFavorites,
						BlogCommentLikes,
						 _create_blog_comment_rating_record )

def _update_notes( db, record, intids, users ):
	return _create_rating_record( db, record,
						record.note_ds_id, record.note_id, intids, users,
						NoteFavorites,
						NoteLikes,
						 _create_note_rating_record )

def _update_topics( db, record, intids, users ):
	return _create_rating_record( db, record,
						record.topic_ds_id, record.topic_id, intids, users,
						TopicFavorites,
						TopicLikes,
						 _create_topic_rating_record )

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

COURSE_TABLES = [ ( ForumCommentLikes, ForumCommentsCreated, 'comment_id', ForumCommentsCreated.comment_id ),
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

def _add_future_evolve_columns( connection, op ):
	for table in (BlogCommentsCreated,ForumCommentsCreated,NotesCreated):
		if not _column_exists( connection, table.__tablename__, 'parent_user_id' ):
			op.add_column( table.__tablename__, Column('parent_user_id', Integer, nullable=True) )

	if not _column_exists( connection, 'AssignmentsTaken', 'is_late' ):
		op.add_column( 'AssignmentsTaken', Column('is_late', Boolean, nullable=True) )

	# Add our creator column
	for table, _, _, _ in TABLES:
		if not _column_exists( connection, table.__tablename__, 'creator_id' ):
			op.add_column( table.__tablename__, Column('creator_id', Integer, nullable=False) )

	# Add our course column
	for table, _, _, _ in COURSE_TABLES:
		if not _column_exists( connection, table.__tablename__, 'course_id' ):
			op.add_column( table.__tablename__, Column('course_id', Integer, nullable=False) )

	for table in [ AssignmentViews, SelfAssessmentViews ]:
		if not _column_exists( connection, table.__tablename__, 'assignment_id' ):
			op.add_column( table.__tablename__,
						Column('assignment_id', NTIID_COLUMN_TYPE, nullable=False, index=True ) )

	if not _column_exists( connection, 'Resources', 'max_time_length' ):
		op.add_column( 'Resources', Column( 'max_time_length', Integer, nullable=True ) )

def _evolve_job( intids=None, users=None ):
	site = getSite()
	db = get_analytics_db( strict=False )

	if db is None:
		return

	if intids is None:
		intids = component.getUtility( zope.intid.IIntIds )

	total_faves = total_likes = total_missing = 0

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)
	_add_future_evolve_columns( connection, op )

	for table, _to_call in [	( ForumCommentsCreated, _update_forum_comments ),
								( BlogsCreated, _update_blogs ),
								( BlogCommentsCreated, _update_blog_comments ),
								( NotesCreated, _update_notes ),
								( TopicsCreated, _update_topics ) ]:

		all_records = db.session.query( table ).all()
		for record in all_records:
			if record.favorite_count or record.like_count:
				fave_count, like_count, missing_count = _to_call( db, record, intids, users )
				total_faves += fave_count
				total_likes += like_count
				total_missing += missing_count

	logger.info( '[%s] Added ratings (like=%s) (favorites=%s) (missing=%s)',
				site.__name__, total_likes, total_faves, total_missing )

def do_evolve( context ):
	setHooks()

	db = get_analytics_db( strict=False )

	# Swap out ds_intids for ntiids
	ds_folder = context.connection.root()['nti.dataserver']
	users = ds_folder['users']

	with site( ds_folder ):
		intids = component.getUtility( zope.intid.IIntIds )

		if db is None:
			# Site specific dbs
			run_job_in_all_host_sites( partial( _evolve_job, intids, users ) )
		else:
			# Global db
			_evolve_job( intids, users )


	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve(context):
	"""
	Iterate through the created objects favorites/likes,
	making sure we add the detailed records to the new
	like/favorite tables.
	"""
	do_evolve( context )
