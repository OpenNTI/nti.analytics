#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from six import integer_types
from six import string_types

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import Enum

from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declared_attr

import zope.intid

from nti.dataserver.users.entity import Entity

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import CourseId
from nti.analytics.identifier import NoteId
from nti.analytics.identifier import HighlightId
from nti.analytics.identifier import ResourceId
_sessionid = SessionId()
_courseid = CourseId()
_noteid = NoteId()
_highlightid = HighlightId()
_resourceid = ResourceId()

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import ResourceMixin
from nti.analytics.database.meta_mixins import ResourceViewMixin

from nti.analytics.database.users import get_or_create_user

class NoteMixin(ResourceMixin):

	@declared_attr
	def note_id(cls):
		return Column('note_id', Integer, ForeignKey("NotesCreated.note_id"), nullable=False, index=True )


class NotesCreated(Base,BaseTableMixin,ResourceMixin,DeletedMixin):
	__tablename__ = 'NotesCreated'
	note_id = Column('note_id', Integer, nullable=False, index=True, primary_key=True, autoincrement=False )
	# Parent-id should be other notes; top-level notes will have null parent_ids
	parent_id = Column('parent_id', Integer, nullable=True)
	sharing = Column('sharing', Enum( 'PUBLIC', 'COURSE', 'OTHER', 'UNKNOWN' ), nullable=False )
	note_length = Column('note_length', Integer, nullable=True )

class NotesViewed(Base,BaseViewMixin,NoteMixin):
	__tablename__ = 'NotesViewed'

	__table_args__ = (
        PrimaryKeyConstraint('note_id', 'user_id', 'timestamp'),
    )

class HighlightsCreated(Base,BaseTableMixin,ResourceMixin,DeletedMixin):
	__tablename__ = 'HighlightsCreated'
	highlight_id = Column('highlight_id', Integer, nullable=False, index=True, primary_key=True, autoincrement=False )


def _get_sharing_enum( note, course ):
	# Logic duped in coursewarereports.views.admin_views
	public_scope, = course.SharingScopes.getAllScopesImpliedbyScope('Public')
	other_scopes = [x for x in course.SharingScopes.values() if x != public_scope]

	# Note: we could also do private if not shared at all
	# or perhaps we want to store who we're sharing to.
	result = 'OTHER'

	if public_scope in note.sharingTargets:
		result = 'PUBLIC'
	else:
		for course_only_scope in other_scopes:
			if course_only_scope in note.sharingTargets:
				result = 'COURSE'
				break

	return result

def create_note(user, nti_session, course, note):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	rid = _resourceid.get_id( note.containerId )
	nid = _noteid.get_id( note )
	course_id = _courseid.get_id( course )
	timestamp = get_created_timestamp( note )
	sharing = _get_sharing_enum( note, course )

	note_length = sum( len( x ) for x in note.body )

	pid = None
	parent_note = getattr( note, 'inReplyTo', None )
	if parent_note is not None:
		pid = _noteid.get_id( parent_note )

	new_object = NotesCreated( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								note_id=nid,
								resource_id=rid,
								parent_id=pid,
								note_length=note_length,
								sharing=sharing )
	db.session.add( new_object )

def delete_note(timestamp, note_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	note = db.session.query(NotesCreated).filter(
							NotesCreated.note_id == note_id ).one()
	note.deleted=timestamp
	db.session.flush()

def create_note_view(user, nti_session, timestamp, course, note):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	rid = _resourceid.get_id( note.containerId )
	nid = _noteid.get_id( note )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )

	new_object = NotesViewed( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								resource_id=rid,
								note_id=nid )
	db.session.add( new_object )

def create_highlight(user, nti_session, course, highlight):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	rid = _resourceid.get_id( highlight.containerId )
	hid = _highlightid.get_id( highlight )
	course_id = _courseid.get_id( course )

	timestamp = get_created_timestamp( highlight )

	new_object = HighlightsCreated( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									highlight_id=hid,
									resource_id=rid)
	db.session.add( new_object )

def delete_highlight(timestamp, highlight_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	highlight = db.session.query(HighlightsCreated).filter(
								HighlightsCreated.highlight_id == highlight_id ).one()
	highlight.deleted=timestamp
	db.session.flush()


def get_notes_created_for_course(course):
	db = get_analytics_db()
	course_id = _courseid.get_id( course )
	results = db.session.query(NotesCreated).filter( 	NotesCreated.course_id == course_id,
														NotesCreated.deleted == None  ).all()
	return results

def get_highlights_created_for_course(course):
	db = get_analytics_db()
	course_id = _courseid.get_id( course )
	results = db.session.query(HighlightsCreated).filter( HighlightsCreated.course_id == course_id,
															HighlightsCreated.deleted == None  ).all()
	return results

