#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import Enum

from sqlalchemy.schema import Sequence
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declared_attr

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_ratings
from nti.analytics.common import get_creator

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import NoteId
from nti.analytics.identifier import HighlightId
from nti.analytics.identifier import ResourceId

from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import ResourceMixin
from nti.analytics.database.meta_mixins import RatingsMixin

from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.root_context import get_root_context_id
from nti.analytics.database.resources import get_resource_id

from nti.analytics.database._utils import get_context_path

class NoteMixin(ResourceMixin):

	@declared_attr
	def note_id(cls):
		return Column('note_id', Integer, ForeignKey("NotesCreated.note_id"), nullable=False, index=True )


class NotesCreated(Base,BaseTableMixin,ResourceMixin,DeletedMixin,RatingsMixin):
	__tablename__ = 'NotesCreated'
	note_ds_id = Column('note_ds_id', INTID_COLUMN_TYPE, index=True, nullable=True, unique=False, autoincrement=False )
	note_id = Column('note_id', Integer, Sequence( 'note_seq' ), index=True, nullable=False, primary_key=True )

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
	highlight_ds_id = Column('highlight_ds_id', INTID_COLUMN_TYPE, index=True, nullable=True, autoincrement=False )
	highlight_id = Column('highlight_id', Integer, Sequence( 'highlight_seq' ), index=True, nullable=False, primary_key=True )


def _get_sharing_enum( note, course ):
	# Logic duped in coursewarereports.views.admin_views
	# We may have many values here (course subinstance + parent)

	# Note: we could also do private if not shared at all
	# or perhaps we want to store who we're sharing to.
	result = 'OTHER'

	sharing_scopes = getattr( course, 'SharingScopes', None )
	if sharing_scopes is None:
		# Content package
		return result

	public_scopes = sharing_scopes.getAllScopesImpliedbyScope('Public')
	other_scopes = [x for x in sharing_scopes.values() if x not in public_scopes]

	def _intersect( set1, set2 ):
		return any( x in set1 for x in set2 )

	if _intersect( public_scopes, note.sharingTargets ):
		result = 'PUBLIC'
	elif _intersect( other_scopes, note.sharingTargets ):
		result = 'COURSE'

	return result

def _get_note_id( db, note_ds_id ):
	note = db.session.query(NotesCreated).filter( NotesCreated.note_ds_id == note_ds_id ).first()
	return note and note.note_id

_note_exists = _get_note_id

def create_note(user, nti_session, course, note):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	rid = ResourceId.get_id( note.containerId )
	rid = get_resource_id( db, rid, create=True )

	note_ds_id = NoteId.get_id( note )

	if _note_exists( db, note_ds_id ):
		logger.warn( 'Note already exists (ds_id=%s) (user=%s)',
					note_ds_id, user )
		return

	course_id = get_root_context_id( db, course, create=True )
	timestamp = get_created_timestamp( note )
	sharing = _get_sharing_enum( note, course )
	like_count, favorite_count, is_flagged = get_ratings( note )

	note_length = sum( len( x ) for x in note.body )

	pid = None
	parent_note = getattr( note, 'inReplyTo', None )
	if parent_note is not None:
		pid = NoteId.get_id( parent_note )
		pid = _get_note_id( db, pid )

		if pid is None:
			note_creator = get_creator( parent_note )
			new_note = create_note( note_creator, None, course, parent_note )
			pid = new_note.note_id
			logger.info( 'Created parent note (user=%s) (note=%s)', note_creator, parent_note )

	new_object = NotesCreated( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								note_ds_id=note_ds_id,
								resource_id=rid,
								parent_id=pid,
								note_length=note_length,
								sharing=sharing,
								like_count=like_count,
								favorite_count=favorite_count,
								is_flagged=is_flagged )
	db.session.add( new_object )
	db.session.flush()
	return new_object

def delete_note(timestamp, note_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id ).first()
	if not note:
		logger.info( 'Note never created (%s)', note_ds_id )
		return
	note.deleted=timestamp
	note.note_ds_id = None
	db.session.flush()

def like_note( note, delta ):
	db = get_analytics_db()
	note_ds_id = NoteId.get_id( note )
	db_note = db.session.query(NotesCreated).filter( NotesCreated.note_ds_id == note_ds_id ).one()
	db_note.like_count += delta
	db.session.flush()

def favorite_note( note, delta ):
	db = get_analytics_db()
	note_ds_id = NoteId.get_id( note )
	db_note = db.session.query(NotesCreated).filter( NotesCreated.note_ds_id == note_ds_id ).one()
	db_note.favorite_count += delta
	db.session.flush()

def flag_note( note, state ):
	db = get_analytics_db()
	note_ds_id = NoteId.get_id( note )
	db_note = db.session.query(NotesCreated).filter( NotesCreated.note_ds_id == note_ds_id ).one()
	db_note.is_flagged = state
	db.session.flush()

def _note_view_exists( db, note_id, user_id, timestamp ):
	return db.session.query( NotesViewed ).filter(
							NotesViewed.note_id == note_id,
							NotesViewed.user_id == user_id,
							NotesViewed.timestamp == timestamp ).first()

def create_note_view(user, nti_session, timestamp, context_path, course, note):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	rid = ResourceId.get_id( note.containerId )
	rid = get_resource_id( db, rid, create=True )

	note_ds_id = NoteId.get_id( note )
	note_id = _get_note_id( db, note_ds_id )
	if note_id is None:
		note_creator = get_creator( note )
		new_note = create_note( note_creator, None, course, note )
		note_id = new_note.note_id
		logger.info( 'Created note (user=%s) (note=%s)', note_creator, note_id )

	course_id = get_root_context_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )

	if _note_view_exists( db, note_id, uid, timestamp ):
		logger.warn( 'Note view already exists (user=%s) (note_id=%s)',
					user, note_id )
		return

	context_path = get_context_path( context_path )

	new_object = NotesViewed( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								context_path=context_path,
								resource_id=rid,
								note_id=note_id )
	db.session.add( new_object )

def _highlight_exists( db, highlight_ds_id ):
	return db.session.query( HighlightsCreated ).filter(
							HighlightsCreated.highlight_ds_id == highlight_ds_id ).count()

def create_highlight(user, nti_session, course, highlight):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	rid = ResourceId.get_id( highlight.containerId )
	rid = get_resource_id( db, rid, create=True )

	highlight_ds_id = HighlightId.get_id( highlight )

	if _highlight_exists( db, highlight_ds_id ):
		logger.warn( 'Highlight already exists (ds_id=%s) (user=%s)',
					highlight_ds_id, user )
		return

	course_id = get_root_context_id( db, course, create=True )
	timestamp = get_created_timestamp( highlight )

	new_object = HighlightsCreated( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									highlight_ds_id=highlight_ds_id,
									resource_id=rid)
	db.session.add( new_object )

def delete_highlight(timestamp, highlight_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	highlight = db.session.query(HighlightsCreated).filter(
								HighlightsCreated.highlight_ds_id == highlight_ds_id ).first()
	if not highlight:
		logger.info( 'Highlight never created (%s)', highlight_ds_id )
		return
	highlight.deleted=timestamp
	highlight.highlight_ds_id = None
	db.session.flush()


def get_notes_created_for_course(course):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	results = db.session.query(NotesCreated).filter( 	NotesCreated.course_id == course_id,
														NotesCreated.deleted == None  ).all()
	return results

def get_highlights_created_for_course(course):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	results = db.session.query(HighlightsCreated).filter( HighlightsCreated.course_id == course_id,
															HighlightsCreated.deleted == None  ).all()
	return results

