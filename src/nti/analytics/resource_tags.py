#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from datetime import datetime

from contentratings.interfaces import IObjectRatedEvent

from nti.dataserver.interfaces import IBookmark
from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IObjectFlaggedEvent
from nti.dataserver.interfaces import IObjectFlaggingEvent
from nti.dataserver.users.users import User

from nti.ntiids import ntiids

from nti.intid.interfaces import IIntIdAddedEvent
from nti.intid.interfaces import IIntIdRemovedEvent

from nti.analytics.interfaces import IObjectProcessor

from nti.analytics.sessions import get_nti_session_id

from nti.analytics.common import get_creator
from nti.analytics.common import process_event
from nti.analytics.common import get_rating_from_event

from nti.analytics.resolvers import get_root_context

from nti.analytics.database import resource_tags as db_resource_tags

from nti.analytics.identifier import NoteId
from nti.analytics.identifier import HighlightId
from nti.analytics.identifier import BookmarkId

from nti.analytics import get_factory
from nti.analytics import TAGS_ANALYTICS

get_note_view_count = db_resource_tags.get_note_view_count
get_notes = db_resource_tags.get_notes
get_highlights = db_resource_tags.get_highlights
get_bookmarks = db_resource_tags.get_bookmarks

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( TAGS_ANALYTICS )

def _get_course( obj ):
	__traceback_info__ = obj.containerId
	result = get_root_context( obj )
	return result

# Notes
def _add_note( oid, nti_session=None ):
	note = ntiids.find_object_with_ntiid( oid )
	if note is not None:
		user = get_creator( note )
		course = _get_course( note )
		db_resource_tags.create_note( user, nti_session, course, note )
		logger.debug( 	"Note created (user=%s) (course=%s) (note=%s)",
						user,
						getattr( course, '__name__', course ),
						note )

def _remove_note( note_id, timestamp=None ):
	db_resource_tags.delete_note( timestamp, note_id )
	logger.debug( "Note deleted (note=%s)", note_id )

def _flag_note( oid, state=False ):
	note = ntiids.find_object_with_ntiid( oid )
	if note is not None:
		db_resource_tags.flag_note( note, state )
		logger.debug( 'Note flagged (note=%s) (state=%s)', note, state )

def _favorite_note( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	note = ntiids.find_object_with_ntiid( oid )
	if note is not None:
		user = User.get_user( username )
		db_resource_tags.favorite_note( note, user, nti_session, timestamp, delta )
		logger.debug( 'Note favorite (note=%s)', note )

def _like_note( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	note = ntiids.find_object_with_ntiid( oid )
	if note is not None:
		user = User.get_user( username )
		db_resource_tags.like_note( note, user, nti_session, timestamp, delta )
		logger.debug( 'Note liked (note=%s)', note )

@component.adapter( IObjectFlaggingEvent )
def _note_flagged( event ):
	obj = event.object
	state = True if IObjectFlaggedEvent.providedBy( event ) else False
	if _is_note( obj ):
		process_event( _get_job_queue, _flag_note, obj, state=state )

@component.adapter( IObjectRatedEvent )
def _note_rated( event ):
	obj = event.object
	if _is_note( obj ):
		timestamp = event.rating.timestamp
		nti_session = get_nti_session_id()
		is_favorite, delta = get_rating_from_event( event )
		to_call = _favorite_note if is_favorite else _like_note
		process_event( _get_job_queue, to_call, obj,
					username=event.rating.userid,
					delta=delta,
					nti_session=nti_session,
					timestamp=timestamp )

@component.adapter(	INote, IIntIdAddedEvent )
def _note_added( obj, event ):
	if _is_note( obj ):
		nti_session = get_nti_session_id()
		process_event( _get_job_queue, _add_note, obj, nti_session=nti_session )

@component.adapter(	INote, IIntIdRemovedEvent )
def _note_removed( obj, event ):
	if _is_note( obj ):
		timestamp = datetime.utcnow()
		note_id = NoteId.get_id( obj )
		process_event( _get_job_queue, _remove_note, note_id=note_id, timestamp=timestamp )




# Highlights
def _add_highlight( oid, nti_session=None ):
	highlight = ntiids.find_object_with_ntiid( oid )
	if highlight is not None:
		user = get_creator( highlight )
		course = _get_course( highlight )
		db_resource_tags.create_highlight( user, nti_session, course, highlight )
		logger.debug( "Highlight created (user=%s) (course=%s)",
					user,
					getattr( course, '__name__', course ) )

def _remove_highlight( highlight_id, timestamp=None ):
	db_resource_tags.delete_highlight( timestamp, highlight_id )
	logger.debug( "Highlight deleted (highlight_id=%s)", highlight_id )

@component.adapter(	IHighlight, IIntIdAddedEvent )
def _highlight_added( obj, event ):
	if _is_highlight( obj ):
		nti_session = get_nti_session_id()
		process_event( _get_job_queue, _add_highlight, obj, nti_session=nti_session )

@component.adapter(	IHighlight, IIntIdRemovedEvent )
def _highlight_removed( obj, event ):
	if _is_highlight( obj ):
		timestamp = datetime.utcnow()
		highlight_id = HighlightId.get_id( obj )
		process_event( _get_job_queue, _remove_highlight, highlight_id=highlight_id, timestamp=timestamp )


# Bookmarks
def _add_bookmark( oid, nti_session=None ):
	bookmark = ntiids.find_object_with_ntiid( oid )
	if bookmark is not None:
		user = get_creator( bookmark )
		course = _get_course( bookmark )
		db_resource_tags.create_bookmark( user, nti_session, course, bookmark )
		logger.debug( "Bookmark created (user=%s) (course=%s)",
					user,
					getattr( course, '__name__', course ) )

def _remove_bookmark( bookmark_id, timestamp=None ):
	db_resource_tags.delete_bookmark( timestamp, bookmark_id )
	logger.debug( "Bookmark deleted (bookmark_id=%s)", bookmark_id )

@component.adapter(	IBookmark, IIntIdAddedEvent )
def _bookmark_added( obj, event ):
	nti_session = get_nti_session_id()
	process_event( _get_job_queue, _add_bookmark, obj, nti_session=nti_session )

@component.adapter(	IBookmark, IIntIdRemovedEvent )
def _bookmark_removed( obj, event ):
	timestamp = datetime.utcnow()
	bookmark_id = BookmarkId.get_id( obj )
	process_event( _get_job_queue, _remove_bookmark, bookmark_id=bookmark_id, timestamp=timestamp )

component.moduleProvides( IObjectProcessor )

def _is_note( obj ):
	return INote.providedBy( obj )

def _is_highlight( obj ):
	return 	IHighlight.providedBy( obj ) \
		and not INote.providedBy( obj )

def init( obj ):
	result = True
	if 	_is_note( obj ):
		process_event( _get_job_queue, _add_note, obj )
	elif _is_highlight( obj ):
		process_event( _get_job_queue, _add_highlight, obj )
	elif IBookmark.providedBy( obj ):
		process_event( _get_job_queue, _add_bookmark, obj )
	else:
		result = False
	return result
