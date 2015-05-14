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
from sqlalchemy.orm.session import make_transient
from sqlalchemy.ext.declarative import declared_attr

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_ratings
from nti.analytics.common import get_creator

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import NoteId
from nti.analytics.identifier import HighlightId
from nti.analytics.identifier import BookmarkId
from nti.analytics.identifier import ResourceId

from nti.analytics.read_models import AnalyticsNote
from nti.analytics.read_models import AnalyticsHighlight
from nti.analytics.read_models import AnalyticsBookmark

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import INTID_COLUMN_TYPE

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import ResourceMixin
from nti.analytics.database.meta_mixins import RatingsMixin
from nti.analytics.database.meta_mixins import CreatorMixin
from nti.analytics.database.meta_mixins import CourseMixin

from nti.analytics.database.users import get_user
from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.root_context import get_root_context
from nti.analytics.database.root_context import get_root_context_id
from nti.analytics.database.resources import get_resource_id

from nti.analytics.database._utils import resolve_like
from nti.analytics.database._utils import resolve_favorite
from nti.analytics.database._utils import get_filtered_records
from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_ratings_for_user_objects
from nti.analytics.database._utils import get_replies_to_user as _get_replies_to_user
from nti.analytics.database._utils import get_user_replies_to_others as _get_user_replies_to_others

from . import resolve_objects

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
	parent_user_id = Column('parent_user_id', Integer, index=True, nullable=True)
	sharing = Column('sharing', Enum( 'PUBLIC', 'COURSE', 'OTHER', 'UNKNOWN' ), nullable=False )
	note_length = Column('note_length', Integer, nullable=True )

class NotesViewed(Base,BaseViewMixin,NoteMixin):
	__tablename__ = 'NotesViewed'

	__table_args__ = (
        PrimaryKeyConstraint('note_id', 'user_id', 'timestamp'),
    )

class NoteRatingMixin(CreatorMixin, CourseMixin):

	@declared_attr
	def note_id(cls):
		return Column('note_id', Integer, ForeignKey("NotesCreated.note_id"), nullable=False, index=True )


class NoteFavorites(Base,BaseTableMixin,NoteRatingMixin):
	__tablename__ = 'NoteFavorites'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'note_id'),
    )

class NoteLikes(Base,BaseTableMixin,NoteRatingMixin):
	__tablename__ = 'NoteLikes'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'note_id'),
    )


class HighlightsCreated(Base,BaseTableMixin,ResourceMixin,DeletedMixin):
	__tablename__ = 'HighlightsCreated'
	highlight_ds_id = Column('highlight_ds_id', INTID_COLUMN_TYPE, index=True,
							nullable=True, autoincrement=False )
	highlight_id = Column('highlight_id', Integer, Sequence( 'highlight_seq' ), index=True,
							nullable=False, primary_key=True )

class BookmarksCreated(Base,BaseTableMixin,ResourceMixin,DeletedMixin):
	"""
	Store bookmarks on content objects.
	"""
	__tablename__ = 'BookmarksCreated'
	bookmark_ds_id = Column('bookmark_ds_id', INTID_COLUMN_TYPE, index=True,
							nullable=True, autoincrement=False )
	bookmark_id = Column('bookmark_id', Integer, Sequence( 'bookmark_seq' ), index=True,
							nullable=False, primary_key=True )


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

def _get_note( db, note_ds_id ):
	note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id ).first()
	return note

def _get_note_id( db, note_ds_id ):
	note = _get_note( db, note_ds_id )
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

	# FIXME Will have to handle modeled content
	note_length = sum( len( x ) for x in note.body )

	parent_id = parent_user_id = None
	parent_note = getattr( note, 'inReplyTo', None )

	if parent_note is not None:
		pid = NoteId.get_id( parent_note )
		parent_note_record = _get_note( db, pid )
		if parent_note_record:
			parent_id = parent_note_record.note_id
			parent_user_id = parent_note_record.user_id
		else:
			# We need to create our parent record
			note_creator = get_creator( parent_note )
			new_note = create_note( note_creator, None, course, parent_note )
			parent_id = new_note.note_id
			parent_user_id = new_note.user_id
			logger.info( 'Created parent note (user=%s) (note=%s)', note_creator, parent_note )

	new_object = NotesCreated( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								note_ds_id=note_ds_id,
								resource_id=rid,
								parent_id=parent_id,
								parent_user_id=parent_user_id,
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

def _get_note_rating_record( db, table, user_id, note_id ):
	note_rating_record = db.session.query( table ).filter(
									table.user_id == user_id,
									table.note_id == note_id ).first()
	return note_rating_record

def _create_note_rating_record( db, table, user, session_id, timestamp, note_id, delta, creator_id, course_id ):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user( user )
		user_id = user_record.user_id

		note_rating_record = _get_note_rating_record( db, table,
													user_id, note_id )

		if not note_rating_record and delta > 0:
			# Create
			timestamp = timestamp_type( timestamp )
			note_rating_record = table( note_id=note_id,
								user_id=user_id,
								timestamp=timestamp,
								session_id=session_id,
								creator_id=creator_id,
								course_id=course_id )
			db.session.add( note_rating_record )
		elif note_rating_record and delta < 0:
			# Delete
			db.session.delete( note_rating_record )

def like_note( note, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	note_ds_id = NoteId.get_id( note )
	db_note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id ).first()

	if db_note is not None:
		db_note.like_count += delta
		db.session.flush()
		creator_id = db_note.user_id
		note_id = db_note.note_id
		course_id = db_note.course_id
		_create_note_rating_record( db, NoteLikes, user,
								session_id, timestamp,
								note_id, delta, creator_id, course_id )

def favorite_note( note, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	note_ds_id = NoteId.get_id( note )
	db_note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id ).first()

	if db_note is not None:
		db_note.favorite_count += delta
		db.session.flush()
		creator_id = db_note.user_id
		note_id = db_note.note_id
		course_id = db_note.course_id
		_create_note_rating_record( db, NoteFavorites, user,
								session_id, timestamp,
								note_id, delta, creator_id, course_id )

def flag_note( note, state ):
	db = get_analytics_db()
	note_ds_id = NoteId.get_id( note )
	db_note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id ).first()
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


def _bookmark_exists( db, bookmark_ds_id ):
	return db.session.query( BookmarksCreated ).filter(
							BookmarksCreated.bookmark_ds_id == bookmark_ds_id ).count()

def create_bookmark(user, nti_session, course, bookmark):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	rid = ResourceId.get_id( bookmark.containerId )
	rid = get_resource_id( db, rid, create=True )

	bookmark_ds_id = BookmarkId.get_id( bookmark )

	if _bookmark_exists( db, bookmark_ds_id ):
		logger.warn( 'Bookmark already exists (ds_id=%s) (user=%s)',
					bookmark_ds_id, user )
		return

	course_id = get_root_context_id( db, course, create=True )
	timestamp = get_created_timestamp( bookmark )

	new_object = BookmarksCreated( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									bookmark_ds_id=bookmark_ds_id,
									resource_id=rid)
	db.session.add( new_object )

def delete_bookmark(timestamp, bookmark_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	bookmark = db.session.query(BookmarksCreated).filter(
								BookmarksCreated.bookmark_ds_id == bookmark_ds_id ).first()
	if not bookmark:
		logger.info( 'Bookmark never created (%s)', bookmark_ds_id )
		return
	bookmark.deleted=timestamp
	bookmark.bookmark_ds_id = None
	db.session.flush()

def _resolve_note( row, user=None, course=None ):
	make_transient( row )
	note = NoteId.get_object( row.note_ds_id )
	course = get_root_context( row.course_id ) if course is None else course
	user = get_user( row.user_id ) if user is None else user
	is_reply = row.parent_id is not None

	result = None
	if 		note is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsNote( Note=note,
								user=user,
								timestamp=row.timestamp,
								RootContext=course,
								NoteLength=row.note_length,
								Sharing=row.sharing,
								IsReply=is_reply )
	return result

def get_notes( user, course=None, timestamp=None, get_deleted=False, top_level_only=False, replies_only=False ):
	"""
	Fetch any notes for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted, or whether the note is a reply (or top-level).
	"""
	filters = []
	if not get_deleted:
		filters.append( NotesCreated.deleted == None )

	if top_level_only:
		filters.append( NotesCreated.parent_id == None )
	elif replies_only:
		filters.append( NotesCreated.parent_id != None )
	results = get_filtered_records( user, NotesCreated, course=course,
								timestamp=timestamp, filters=filters )
	return resolve_objects( _resolve_note, results, user=user, course=course )

def get_likes_for_users_notes( user, course=None, timestamp=None ):
	"""
	Fetch any likes created for a user's notes *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( NoteLikes, user, course, timestamp )
	return resolve_objects( resolve_like, results, obj_creator=user)

def get_favorites_for_users_notes( user, course=None, timestamp=None ):
	"""
	Fetch any favorites created for a user's notes *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( NoteFavorites, user, course, timestamp )
	return resolve_objects( resolve_favorite, results, obj_creator=user )

def get_user_replies_to_others( user, course=None, timestamp=None, get_deleted=False ):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	results = _get_user_replies_to_others( NotesCreated, user, course, timestamp, get_deleted )
	return resolve_objects( _resolve_note, results, user=user, course=course )

def get_replies_to_user( user, course=None, timestamp=None, get_deleted=False  ):
	"""
	Fetch any replies to our user, *after* the optionally given timestamp.
	"""
	results = _get_replies_to_user( NotesCreated, user, course, timestamp, get_deleted )
	return resolve_objects( _resolve_note, results, course=course )

def get_notes_created_for_course(course):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	results = db.session.query(NotesCreated).filter(
								NotesCreated.course_id == course_id,
								NotesCreated.deleted == None  ).all()
	return resolve_objects( _resolve_note, results, course=course )

def _resolve_highlight( row, user=None, course=None ):
	make_transient( row )
	highlight = HighlightId.get_object( row.highlight_ds_id )
	course = get_root_context( row.course_id ) if course is None else course
	user = get_user( row.user_id ) if user is None else user

	result = None
	if 		highlight is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsHighlight( Highlight=highlight,
								user=user,
								timestamp=row.timestamp,
								RootContext=course )
	return result

def get_highlights( user, course=None, timestamp=None, get_deleted=False ):
	"""
	Fetch any highlights for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	filters = ()
	if not get_deleted:
		filters = (HighlightsCreated.deleted == None,)
	results = get_filtered_records( user, HighlightsCreated, course=course,
								timestamp=timestamp, filters=filters )
	return resolve_objects( _resolve_highlight, results, user=user, course=course )

def get_highlights_created_for_course(course):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	results = db.session.query(HighlightsCreated).filter(
								HighlightsCreated.course_id == course_id,
								HighlightsCreated.deleted == None  ).all()
	return resolve_objects( _resolve_highlight, results, course=course )

def _resolve_bookmark( row, user=None, course=None ):
	make_transient( row )
	bookmark = BookmarkId.get_object( row.bookmark_ds_id )
	course = get_root_context( row.course_id ) if course is None else course
	user = get_user( row.user_id ) if user is None else user

	result = None
	if 		bookmark is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsBookmark( Bookmark=bookmark,
								user=user,
								timestamp=row.timestamp,
								RootContext=course )
	return result

def get_bookmarks( user, course=None, timestamp=None, get_deleted=False ):
	"""
	Fetch any bookmarks for a user started *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	filters = ()
	if not get_deleted:
		filters = (BookmarksCreated.deleted == None,)
	results = get_filtered_records( user, BookmarksCreated, course=course,
								timestamp=timestamp, filters=filters )
	return resolve_objects( _resolve_bookmark, results, user=user, course=course )

def get_note_view_count( note ):
	"""
	Return the number of times this note has been viewed.
	"""
	result = 0
	db = get_analytics_db()
	note_ds_id = NoteId.get_id( note )
	note_id = _get_note_id( db, note_ds_id )
	if note_id is not None:
		result = db.session.query(NotesViewed).filter(
								NotesViewed.note_id == note_id ).count()
	return result

