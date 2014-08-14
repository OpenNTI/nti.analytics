#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.intid import interfaces as intid_interfaces

from nti.ntiids import ntiids

from datetime import datetime

from nti.analytics import interfaces as analytic_interfaces

from .common import get_creator
from .common import get_nti_session_id
from .common import get_deleted_time
from .common import get_object_root
from .common import get_course
from .common import process_event

from nti.analytics.database import boards as db_boards

from nti.analytics.identifier import ForumId
from nti.analytics.identifier import TopicId
from nti.analytics.identifier import CommentId
_commentid = CommentId()
_topicid = TopicId()
_forumid = ForumId()

def get_topics_created_for_user( *args, **kwargs ):
	return db_boards.get_topics_created_for_user( *args, **kwargs  )

def get_forum_comments_for_user( *args, **kwargs  ):
	return db_boards.get_forum_comments_for_user( *args, **kwargs  )


def _is_topic( obj ):
	# Exclude blogs
	result = 	frm_interfaces.ITopic.providedBy(obj) \
			and not (	frm_interfaces.IPersonalBlogEntry.providedBy( obj ) \
					or 	frm_interfaces.IPersonalBlogEntryPost.providedBy( obj ) )
	return result

def _is_forum_comment( obj ):
	result = 	frm_interfaces.IGeneralForumComment.providedBy( obj ) \
			and not frm_interfaces.IPersonalBlogComment.providedBy( obj )
	return result

# Comments
def _add_comment( oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		topic = get_object_root( comment, frm_interfaces.ITopic )
		course = get_course( topic )
		if topic:
			db_boards.create_forum_comment( user, nti_session, course, topic, comment )
			logger.debug( 	"Forum comment created (user=%s) (topic=%s) (course=%s)",
							user,
							getattr( topic, '__name__', topic ),
							getattr( course, '__name__', course ) )

def _remove_comment( comment_id, timestamp ):
	db_boards.delete_forum_comment( timestamp, comment_id )
	logger.debug( "Forum comment deleted (comment_id=%s)", comment_id )

@component.adapter( frm_interfaces.IGeneralForumComment,
					intid_interfaces.IIntIdAddedEvent )
def _add_general_forum_comment(comment, event):
	if _is_forum_comment( comment ):
		user = get_creator( comment )
		nti_session = get_nti_session_id( user )
		process_event( _add_comment, comment, nti_session=nti_session )

@component.adapter(frm_interfaces.IGeneralForumComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_general_forum_comment(comment, event):
	if		_is_forum_comment( comment ) \
		and nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
			timestamp = datetime.utcnow()
			comment_id = _commentid.get_id( comment )
			process_event( _remove_comment, comment_id=comment_id, timestamp=timestamp )

# Topic
def _add_topic( oid, nti_session=None ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		user = get_creator( topic )
		course = get_course( topic )
		db_boards.create_topic( user, nti_session, course, topic )
		logger.debug( "Topic created (user=%s) (topic=%s)",
					user,
					getattr( topic, '__name__', topic ))

def _remove_topic( topic_id, timestamp=None ):
	db_boards.delete_topic( timestamp, topic_id )
	logger.debug( "Topic deleted (topic_id=%s)", topic_id )

@component.adapter( frm_interfaces.ITopic, intid_interfaces.IIntIdAddedEvent )
def _topic_added( topic, event ):
	if _is_topic( topic ):
		user = get_creator( topic )
		nti_session = get_nti_session_id( user )
		process_event( _add_topic, topic, nti_session=nti_session )

@component.adapter( frm_interfaces.ITopic, intid_interfaces.IIntIdRemovedEvent )
def _topic_removed( topic, event ):
	if _is_topic( topic ):
		timestamp = datetime.utcnow()
		topic_id = _topicid.get_id( topic )
		process_event( _remove_topic, topic_id=topic_id, timestamp=timestamp )

# Forum
def _remove_forum( forum_id, timestamp ):
	db_boards.delete_forum( timestamp, forum_id )
	logger.debug( "Forum deleted (forum_id=%s)", forum_id )

def _add_forum( oid, nti_session=None ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		user = get_creator( forum )
		course = get_course( forum )
		db_boards.create_forum( user, nti_session, course, forum )
		logger.debug( 	"Forum created (user=%s) (forum=%s) (course=%s)",
						user,
						getattr( forum, '__name__', forum ),
						getattr( course, '__name__', course ) )

@component.adapter( frm_interfaces.IForum, intid_interfaces.IIntIdAddedEvent )
def _forum_added( forum, event ):
	user = get_creator( forum )
	nti_session = get_nti_session_id( user )
	process_event( _add_forum, forum, nti_session=nti_session )

@component.adapter( frm_interfaces.IForum, intid_interfaces.IIntIdRemovedEvent )
def _forum_removed( forum, event ):
	timestamp = datetime.utcnow()
	timestamp = get_deleted_time( forum )
	forum_id = _forumid.get_id( forum )
	process_event( _remove_forum, forum_id=forum_id, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	result = True
	if frm_interfaces.IForum.providedBy(obj):
		process_event( _add_forum, obj )
	elif _is_topic( obj ):
		process_event( _add_topic, obj )
	elif _is_forum_comment( obj ):
		process_event( _add_comment, obj )
	else:
		result = False

	return result