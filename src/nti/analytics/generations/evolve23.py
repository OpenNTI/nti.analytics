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

from nti.dataserver.liking import LIKE_CAT_NAME
from nti.dataserver.liking import FAVR_CAT_NAME
from nti.dataserver.rating import lookup_rating_for_read

from nti.analytics.database import get_analytics_db

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

def _evolve_job( intids=None, users=None ):
	site = getSite()
	db = get_analytics_db( strict=False )

	if db is None:
		return

	if intids is None:
		intids = component.getUtility( zope.intid.IIntIds )

	total_faves = total_likes = total_missing = 0

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
