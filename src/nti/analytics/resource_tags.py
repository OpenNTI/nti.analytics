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

from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

from nti.intid import interfaces as intid_interfaces

from nti.analytics import interfaces as analytic_interfaces

from .common import get_creator
from .common import get_nti_session_id
from .common import process_event
from .common import get_course_by_ntiid
from .common import get_course

from nti.analytics.database import resource_tags as db_resource_tags

from nti.analytics.identifier import NoteId
from nti.analytics.identifier import HighlightId
_noteid = NoteId()
_highlightid = HighlightId()

def _get_course( obj ):
	__traceback_info__ = obj.containerId
	result = get_course_by_ntiid( obj.containerId )
	return result

# Notes
def _add_note( oid, nti_session=None ):
	note = ntiids.find_object_with_ntiid( oid )
	if note is not None:
		user = get_creator( note )
		course = _get_course( note )
		db_resource_tags.create_note( user, nti_session, course, note )
		logger.debug( 	"Note created (user=%s) (course=%s) (note=%s)",
						user, course, note )

def _remove_note( note_id, timestamp=None ):
	db_resource_tags.delete_note( timestamp, note_id )
	logger.debug( "Note deleted (note=%s)", note_id )

@component.adapter(	nti_interfaces.INote,
					intid_interfaces.IIntIdAddedEvent )
def _note_added( obj, event ):
	if _is_note( obj ):
		user = get_creator( obj )
		nti_session = get_nti_session_id( user )
		process_event( _add_note, obj, nti_session=nti_session )

@component.adapter(	nti_interfaces.INote,
					intid_interfaces.IIntIdRemovedEvent )
def _note_removed( obj, event ):
	if _is_note( obj ):
		timestamp = datetime.utcnow()
		note_id = _noteid.get_id( obj )
		process_event( _remove_note, note_id=note_id, timestamp=timestamp )


# Highlights
def _add_highlight( oid, nti_session=None ):
	highlight = ntiids.find_object_with_ntiid( oid )
	if highlight is not None:
		user = get_creator( highlight )
		course = _get_course( highlight )
		db_resource_tags.create_highlight( user, nti_session, course, highlight )
		logger.debug( "Highlight created (user=%s) (course=%s)", user, course )

def _remove_highlight( highlight_id, timestamp=None ):
	db_resource_tags.delete_highlight( timestamp, highlight_id )
	logger.debug( "Highlight deleted (highlight_id=%s)", highlight_id )

@component.adapter(	nti_interfaces.IHighlight,
					intid_interfaces.IIntIdAddedEvent )
def _highlight_added( obj, event ):
	if _is_highlight( obj ):
		user = get_creator( obj )
		nti_session = get_nti_session_id( user )
		process_event( _add_highlight, obj, nti_session=nti_session )

@component.adapter(	nti_interfaces.IHighlight,
					intid_interfaces.IIntIdRemovedEvent )
def _highlight_removed( obj, event ):
	if _is_highlight( obj ):
		timestamp = datetime.utcnow()
		highlight_id = _highlightid.get_id( obj )
		process_event( _remove_highlight, highlight_id=highlight_id, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def _is_note( obj ):
	return nti_interfaces.INote.providedBy( obj )

def _is_highlight( obj ):
	return 	nti_interfaces.IHighlight.providedBy( obj ) \
		and not nti_interfaces.INote.providedBy( obj )

def init( obj ):
	result = True
	if 	_is_note( obj ):
		process_event( _add_note, obj )
	elif _is_highlight( obj ):
		process_event( _add_highlight, obj )
	else:
		result = False
	return result
