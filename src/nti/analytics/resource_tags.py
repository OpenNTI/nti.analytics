#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.intid import interfaces as intid_interfaces
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.ntiids import ntiids

from .common import get_creator
from .common import get_nti_session
from .common import to_external_ntiid_oid
from .common import get_deleted_time
from .common import get_comment_root
from .common import process_event
from .common import get_course_by_ntiid

from . import utils
from . import create_job
from . import get_job_queue
from . import interfaces as analytic_interfaces

def get_course( obj ):
	return get_course_by_ntiid( obj.containerId )

# Notes
def _add_note( db, oid ):
	note = ntiids.find_object_with_ntiid( oid )
	if note is not None:
		user = get_creator( note )
		nti_session = get_nti_session()
		course = get_course( note )
		db.create_note( user, nti_session, course, note )
		logger.debug( "Note created (user=%s) (course=%s)", user, course )

def _remove_highlight( db, oid, timestamp=None ):
	note = ntiids.find_object_with_ntiid( oid )
	if note is not None:
		db.delete_note( timestamp, note )
		logger.debug( "Note deleted" )

@component.adapter(	nti_interfaces.INote,
					intid_interfaces.IIntIdAddedEvent )
def _note_added( obj, event ):
	if _is_note( obj ):
		process_event( _add_note, obj )
	
@component.adapter(	nti_interfaces.INote,
					intid_interfaces.IIntIdRemovedEvent )
def _note_removed( obj, event ):
	if _is_note( obj ):
		timestamp = datetime.utcnow()
		process_event( _remove_note, obj, timestamp=timestamp )


# Highlights
def _add_highlight( db, oid ):
	highlight = ntiids.find_object_with_ntiid( oid )
	if highlight is not None:
		user = get_creator( highlight )
		nti_session = get_nti_session()
		course = get_course( highlight )
		db.create_highlight( user, nti_session, course, highlight )
		logger.debug( "Highlight created (user=%s) (course=%s)", user, course )

def _remove_highlight( db, oid, timestamp=None ):
	highlight = ntiids.find_object_with_ntiid( oid )
	if highlight is not None:
		db.delete_highlight( timestamp, highlight )
		logger.debug( "Highlight deleted" )

@component.adapter(	nti_interfaces.IHighlight,
					intid_interfaces.IIntIdAddedEvent )
def _highlight_added( obj, event ):
	if _is_highlight( obj ):
		process_event( _add_highlight, obj )
	
@component.adapter(	nti_interfaces.IHighlight,
					intid_interfaces.IIntIdRemovedEvent )
def _highlight_removed( obj, event ):
	if _is_highlight( obj ):
		timestamp = datetime.utcnow()
		process_event( _remove_highlight, obj, timestamp=timestamp )	
		
component.moduleProvides(analytic_interfaces.IObjectProcessor)

def _is_note( obj ):
	return nti_interfaces.INote.providedBy( obj );

def _is_highlight( obj ):
	return 	nti_interfaces.IHighlight.providedBy( obj ) \
		and not nti_interfaces.INote.providedBy( obj );

def init( obj ):
	result = True
	if 	_is_note( obj ):
		process_event( _add_note, obj )
	elif _is_highlight( obj ):
		process_event( _add_highlight, obj )
	else:
		result = False
	return result
