#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from zope import component
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from nti.ntiids import ntiids
from nti.intid.interfaces import IIntIdAddedEvent
from nti.intid.interfaces import IIntIdRemovedEvent

from contentratings.interfaces import IObjectRatedEvent

from nti.dataserver.interfaces import IObjectFlaggedEvent
from nti.dataserver.interfaces import IObjectFlaggingEvent
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.users.users import User

from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForumComment

from nti.analytics.interfaces import IObjectProcessor
from nti.analytics.sessions import get_nti_session_id

from nti.analytics.common import get_creator
from nti.analytics.common import get_deleted_time
from nti.analytics.common import get_object_root
from nti.analytics.common import process_event
from nti.analytics.common import get_rating_from_event

from nti.analytics.database import boards as db_boards

from .identifier import get_ds_id

from nti.analytics import get_factory
from nti.analytics import BOARDS_ANALYTICS
from nti.analytics import TOPICS_ANALYTICS
from nti.analytics import COMMENTS_ANALYTICS

def _get_board_queue():
	factory = get_factory()
	return factory.get_queue( BOARDS_ANALYTICS )

def _get_topic_queue():
	factory = get_factory()
	return factory.get_queue( TOPICS_ANALYTICS )

def _get_comments_queue():
	factory = get_factory()
	return factory.get_queue( COMMENTS_ANALYTICS )

get_topics_created_for_user = db_boards.get_topics_created_for_user
get_forum_comments_for_user = db_boards.get_forum_comments_for_user
get_forum_comments = db_boards.get_forum_comments
get_topic_views = db_boards.get_topic_views
get_topic_last_view = db_boards.get_topic_last_view
get_replies_to_user = db_boards.get_replies_to_user
get_user_replies_to_others = db_boards.get_user_replies_to_others
get_likes_for_users_topics = db_boards.get_likes_for_users_topics
get_favorites_for_users_topics = db_boards.get_favorites_for_users_topics
get_likes_for_users_comments = db_boards.get_likes_for_users_comments
get_favorites_for_users_comments = db_boards.get_favorites_for_users_comments

def _is_topic( obj ):
	# Exclude blogs
	result = 	ITopic.providedBy(obj) \
			and not (	IPersonalBlogEntry.providedBy( obj ) \
					or 	IPersonalBlogEntryPost.providedBy( obj ) )
	return result

def _is_forum_comment( obj ):
	result = 	IGeneralForumComment.providedBy( obj ) \
			and not IPersonalBlogComment.providedBy( obj )
	return result

# Comments
def _add_comment( oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		topic = get_object_root( comment, ITopic )
		if topic is not None:
			db_boards.create_forum_comment( user, nti_session, topic, comment )
			logger.debug( 	"Forum comment created (user=%s) (topic=%s)",
							user,
							getattr( topic, '__name__', topic ) )

def _remove_comment( comment_id, timestamp ):
	db_boards.delete_forum_comment( timestamp, comment_id )
	logger.debug( "Forum comment deleted (comment_id=%s)", comment_id )

def _flag_comment( oid, state=False ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		db_boards.flag_comment( comment, state )
		logger.debug( 'Comment flagged (comment=%s) (state=%s)', comment, state )

def _favorite_comment( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = User.get_user( username )
		db_boards.favorite_comment( comment, user, nti_session, timestamp, delta )
		logger.debug( 'Comment favorite (comment=%s)', comment )

def _like_comment( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = User.get_user( username )
		db_boards.like_comment( comment, user, nti_session, timestamp, delta )
		logger.debug( 'Comment liked (comment=%s)', comment )

@component.adapter( IGeneralForumComment, IIntIdAddedEvent )
def _add_general_forum_comment(comment, _):
	if _is_forum_comment( comment ):
		nti_session = get_nti_session_id()
		process_event( _get_comments_queue, _add_comment, comment, nti_session=nti_session )

@component.adapter( IGeneralForumComment, IObjectModifiedEvent )
def _modify_general_forum_comment(comment, _):
	if		_is_forum_comment( comment ) \
		and IDeletedObjectPlaceholder.providedBy( comment ):
			timestamp = datetime.utcnow()
			comment_id = get_ds_id( comment )
			process_event( _get_comments_queue, _remove_comment, comment_id=comment_id, timestamp=timestamp )


# Topic
def _add_topic( oid, nti_session=None ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		user = get_creator( topic )
		db_boards.create_topic( user, nti_session, topic )
		logger.debug( "Topic created (user=%s) (topic=%s)",
					user,
					getattr( topic, '__name__', topic ))

def _remove_topic( topic_id, timestamp=None ):
	db_boards.delete_topic( timestamp, topic_id )
	logger.debug( "Topic deleted (topic_id=%s)", topic_id )

def _flag_topic( oid, state=False ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		db_boards.flag_topic( topic, state )
		logger.debug( 'Topic flagged (topic=%s) (state=%s)', topic, state )

def _favorite_topic( oid, username=None, delta=0, timestamp=None, nti_session=None):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		user = User.get_user( username )
		db_boards.favorite_topic( topic, user, nti_session, timestamp, delta )
		logger.debug( 'Topic favorite (topic=%s)', topic )

def _like_topic( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		user = User.get_user( username )
		db_boards.like_topic( topic, user, nti_session, timestamp, delta )
		logger.debug( 'Topic liked (topic=%s)', topic )

@component.adapter( IObjectFlaggingEvent )
def _topic_flagged( event ):
	obj = event.object
	state = True if IObjectFlaggedEvent.providedBy( event ) else False
	if _is_topic( obj ):
		process_event( _get_topic_queue, _flag_topic, obj, state=state )
	elif _is_forum_comment( obj ):
		process_event( _get_comments_queue, _flag_comment, obj, state=state )

@component.adapter( IObjectRatedEvent )
def _topic_rated( event ):
	obj = event.object
	_favorite_call = _like_call = _queue = None

	if _is_topic( obj ):
		_like_call = _like_topic
		_favorite_call = _favorite_topic
		_queue = _get_topic_queue
	elif _is_forum_comment( obj ):
		_like_call = _like_comment
		_favorite_call = _favorite_comment
		_queue = _get_comments_queue

	if _like_call is not None:
		timestamp = event.rating.timestamp
		nti_session = get_nti_session_id()
		is_favorite, delta = get_rating_from_event( event )
		to_call = _favorite_call if is_favorite else _like_call
		process_event( _queue, to_call,
					obj,
					username=event.rating.userid,
					delta=delta,
					nti_session=nti_session,
					timestamp=timestamp )

@component.adapter( ITopic, IIntIdAddedEvent )
def _topic_added( topic, _ ):
	if _is_topic( topic ):
		nti_session = get_nti_session_id()
		process_event( _get_topic_queue, _add_topic, topic, nti_session=nti_session )

@component.adapter( ITopic, IIntIdRemovedEvent )
def _topic_removed( topic, _ ):
	if _is_topic( topic ):
		timestamp = datetime.utcnow()
		topic_id = get_ds_id( topic )
		process_event( _get_topic_queue, _remove_topic, topic_id=topic_id, timestamp=timestamp )


# Forum
def _remove_forum( forum_id, timestamp ):
	db_boards.delete_forum( timestamp, forum_id )
	logger.debug( "Forum deleted (forum_id=%s)", forum_id )

def _add_forum( oid, nti_session=None ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		user = get_creator( forum )
		db_boards.create_forum( user, nti_session, forum )
		logger.debug( 	"Forum created (user=%s) (forum=%s)",
						user,
						getattr( forum, '__name__', forum ) )

@component.adapter( IForum, IIntIdAddedEvent )
def _forum_added( forum, _ ):
	nti_session = get_nti_session_id()
	process_event( _get_board_queue, _add_forum, forum, nti_session=nti_session )

@component.adapter( IForum, IIntIdRemovedEvent )
def _forum_removed( forum, _ ):
	timestamp = get_deleted_time( forum )
	forum_id = get_ds_id( forum )
	process_event( _get_board_queue, _remove_forum, forum_id=forum_id, timestamp=timestamp )

component.moduleProvides( IObjectProcessor )

def init( obj ):
	result = True
	if IForum.providedBy(obj):
		process_event( _get_board_queue, _add_forum, obj )
	elif _is_topic( obj ):
		process_event( _get_topic_queue, _add_topic, obj )
	elif _is_forum_comment( obj ):
		process_event( _get_comments_queue, _add_comment, obj )
	else:
		result = False

	return result
