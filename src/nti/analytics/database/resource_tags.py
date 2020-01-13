#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from sqlalchemy import func

from zope import component

from nti.analytics_database.resource_tags import NoteLikes
from nti.analytics_database.resource_tags import NotesViewed
from nti.analytics_database.resource_tags import NotesCreated
from nti.analytics_database.resource_tags import NoteFavorites
from nti.analytics_database.resource_tags import BookmarksCreated
from nti.analytics_database.resource_tags import HighlightsCreated
from nti.analytics_database.resource_tags import NotesUserFileUploadMimeTypes

from nti.analytics.common import get_creator
from nti.analytics.common import get_ratings
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_created_timestamp

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_body_text_length
from nti.analytics.database._utils import get_root_context_records

from nti.analytics.database.mime_types import build_mime_type_records

from nti.analytics.database.query_utils import resolve_like
from nti.analytics.database.query_utils import resolve_favorite
from nti.analytics.database.query_utils import get_filtered_records
from nti.analytics.database.query_utils import get_ratings_for_user_objects
from nti.analytics.database.query_utils import get_replies_to_user as _get_replies_to_user
from nti.analytics.database.query_utils import get_user_replies_to_others as _get_user_replies_to_others

from nti.analytics.database.resources import get_resource_id

from nti.analytics.database.root_context import get_root_context_record

from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.users import get_user_db_id

from nti.analytics.identifier import get_ds_id
from nti.analytics.identifier import get_ds_object
from nti.analytics.identifier import get_ntiid_id

from nti.analytics.resolvers import get_root_context

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver.users.communities import Community

logger = __import__('logging').getLogger(__name__)


def _get_site_community():
	site_policy = component.queryUtility( ISitePolicyUserEventListener )
	community_username = getattr(site_policy, 'COM_USERNAME', '')
	result = None
	if community_username:
		result = Community.get_community( community_username )
	return result


def _get_sharing_enum(note, course):
	# TODO: Logic needs to be updated in courseware_reports.views.admin_views
	# We may have many values here (course subinstance + parent)
	# Perhaps we want to store who we're sharing to.

	sharing_scopes = getattr(course, 'SharingScopes', None)
	if sharing_scopes is None:
		# Content package
		return 'OTHER'

	# Do we want purchased here?
	public_scopes = set( sharing_scopes.getAllScopesImpliedbyScope('Public') )
	other_scopes = [x for x in sharing_scopes.values() if x not in public_scopes]

	def _intersect(set1, set2):
		return any(x in set1 for x in set2)

	site_community = _get_site_community()

	if not note.sharingTargets:
		result = 'PRIVATE'
	elif site_community and note.isSharedDirectlyWith( site_community ):
		result = 'GLOBAL'
	elif _intersect(public_scopes, note.sharingTargets):
		result = 'PUBLIC_COURSE'
	elif _intersect(other_scopes, note.sharingTargets):
		result = 'PRIVATE_COURSE'
	else:
		# We're shared directly with individuals/groups.
		result = 'OTHER'

	return result


def _get_note(db, note_ds_id):
	note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id).first()
	return note


def _get_note_id(db, note_ds_id):
	note = _get_note(db, note_ds_id)
	return note and note.note_id

_note_exists = _get_note_id


def _set_mime_records( db, note_record, note ):
	"""
	Set the mime type records for our note, removing any
	previous records present.
	"""
	# Delete the old records.
	for mime_record in note_record._file_mime_types:
		db.session.delete( mime_record )
	note_record._file_mime_types = []

	file_mime_types = build_mime_type_records( db, note, NotesUserFileUploadMimeTypes )
	note_record._file_mime_types.extend( file_mime_types )


def _set_note_ratings( note_record, note ):
	like_count, favorite_count, is_flagged = get_ratings(note)
	note_record.like_count = like_count
	note_record.favorite_count = favorite_count
	note_record.is_flagged = is_flagged


def _set_note_attributes( db, note_record, note, course ):
	"""
	Set the note attributes for this note record.
	"""
	note_record.sharing = _get_sharing_enum(note, course)
	_set_note_ratings( note_record, note )
	note_record.note_length = get_body_text_length( note )
	_set_mime_records( db, note_record, note )


def create_note(user, nti_session, note):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	sid = nti_session
	rid = get_ntiid_id(note.containerId)
	rid = get_resource_id(db, rid, create=True)

	note_ds_id = get_ds_id(note)

	if _note_exists(db, note_ds_id):
		logger.warn('Note already exists (ds_id=%s) (user=%s)',
					note_ds_id, user)
		return

	course = get_root_context(note)
	root_context_record = get_root_context_record(db, course, create=True)
	timestamp = get_created_timestamp(note)

	parent_id = parent_user_id = None
	parent_note = getattr(note, 'inReplyTo', None)

	if parent_note is not None:
		pid = get_ds_id(parent_note)
		parent_note_record = _get_note(db, pid)
		if parent_note_record:
			parent_id = parent_note_record.note_id
			parent_user_id = parent_note_record.user_id
		else:
			# We need to create our parent record
			note_creator = get_creator(parent_note)
			new_note = create_note(note_creator, None, parent_note)
			parent_id = new_note.note_id
			parent_user_id = new_note.user_id
			logger.info('Created parent note (user=%s) (note=%s)', note_creator, parent_note)

	new_object = NotesCreated(	session_id=sid,
								timestamp=timestamp,
								note_ds_id=note_ds_id,
								resource_id=rid,
								parent_id=parent_id,
								parent_user_id=parent_user_id)
	_set_note_attributes( db, new_object, note, course )
	new_object._root_context_record = root_context_record
	new_object._user_record = user_record
	db.session.add(new_object)
	return new_object


def update_note(user, nti_session, note):
	"""
	Update our note record, creating if it does not exist.
	"""
	db = get_analytics_db()
	note_ds_id = get_ds_id(note)
	note_record = _get_note(db, note_ds_id)
	if note_record is None:
		create_note(user, nti_session, note)
	else:
		course = get_root_context(note)
		_set_note_attributes( db, note_record, note, course )


def delete_note(timestamp, note_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type(timestamp)
	note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id).first()
	if not note:
		logger.info('Note never created (%s)', note_ds_id)
		return
	note.deleted = timestamp
	note.note_ds_id = None


def _get_note_rating_record(db, table, user_id, note_id):
	note_rating_record = db.session.query(table).filter(
									table.user_id == user_id,
									table.note_id == note_id).first()
	return note_rating_record


def _create_note_rating_record(db, table, user, session_id, timestamp, delta, note_record):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user(user)
		user_id = user_record.user_id
		creator_id = note_record.user_id
		note_id = note_record.note_id
		course_id = note_record.course_id
		entity_root_context_id = note_record.entity_root_context_id

		note_rating_record = _get_note_rating_record(db, table,
													 user_id, note_id)

		if not note_rating_record and delta > 0:
			# Create
			timestamp = timestamp_type(timestamp)
			note_rating_record = table(	note_id=note_id,
										user_id=user_id,
										timestamp=timestamp,
										session_id=session_id,
										creator_id=creator_id,
										course_id=course_id,
										entity_root_context_id=entity_root_context_id)
			db.session.add(note_rating_record)
		elif note_rating_record and delta < 0:
			# Delete
			db.session.delete(note_rating_record)


def like_note(note, user, session_id, timestamp, delta):
	db = get_analytics_db()
	note_ds_id = get_ds_id(note)
	db_note = db.session.query(NotesCreated).filter(
							NotesCreated.note_ds_id == note_ds_id).first()

	if db_note is not None:
		_set_note_ratings( db_note, note )
		_create_note_rating_record(db, NoteLikes, user,
								session_id, timestamp,
								delta, db_note)


def favorite_note(note, user, session_id, timestamp, delta):
	db = get_analytics_db()
	note_ds_id = get_ds_id(note)
	db_note = db.session.query(NotesCreated).filter(
							   NotesCreated.note_ds_id == note_ds_id).first()

	if db_note is not None:
		_set_note_ratings( db_note, note )
		_create_note_rating_record(	db, NoteFavorites, user,
									session_id, timestamp,
									delta, db_note)


def flag_note(note, state):
	db = get_analytics_db()
	note_ds_id = get_ds_id(note)
	db_note = db.session.query(NotesCreated).filter(
							   NotesCreated.note_ds_id == note_ds_id).first()
	db_note.is_flagged = state


def _note_view_exists(db, note_id, user_id, timestamp):
	return db.session.query(NotesViewed).filter(
							NotesViewed.note_id == note_id,
							NotesViewed.user_id == user_id,
							NotesViewed.timestamp == timestamp).first()


def create_note_view(user, nti_session, timestamp, context_path, root_context, note):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	sid = nti_session
	rid = get_ntiid_id(note.containerId)
	rid = get_resource_id(db, rid, create=True)

	note_ds_id = get_ds_id(note)
	note_id = _get_note_id(db, note_ds_id)
	if note_id is None:
		note_creator = get_creator(note)
		new_note = create_note(note_creator, None, note)
		note_id = new_note.note_id
		logger.info('Created note (user=%s) (note=%s)', note_creator, note_id)

	timestamp = timestamp_type(timestamp)

	if _note_view_exists(db, note_id, user_record.user_id, timestamp):
		logger.warn('Note view already exists (user=%s) (note_id=%s)',
					user, note_id)
		return

	context_path = get_context_path(context_path)
	root_context, entity_root_context = get_root_context_records(root_context)

	new_object = NotesViewed(session_id=sid,
							 timestamp=timestamp,
							 context_path=context_path,
							 resource_id=rid,
							 note_id=note_id)
	new_object._user_record = user_record
	new_object._root_context_record = root_context
	new_object._entity_root_context_record = entity_root_context
	db.session.add(new_object)


def _highlight_exists(db, highlight_ds_id):
	return db.session.query(HighlightsCreated).filter(
							HighlightsCreated.highlight_ds_id == highlight_ds_id).count()


def create_highlight(user, nti_session, highlight):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	sid = nti_session
	rid = get_ntiid_id(highlight.containerId)
	rid = get_resource_id(db, rid, create=True)
	highlight_ds_id = get_ds_id(highlight)

	if _highlight_exists(db, highlight_ds_id):
		logger.warn('Highlight already exists (ds_id=%s) (user=%s)',
					highlight_ds_id, user)
		return

	course = get_root_context(highlight)
	root_context_record = get_root_context_record(db, course, create=True)
	timestamp = get_created_timestamp(highlight)

	new_object = HighlightsCreated(	session_id=sid,
									timestamp=timestamp,
									highlight_ds_id=highlight_ds_id,
									resource_id=rid)
	new_object._user_record = user_record
	new_object._root_context_record = root_context_record
	db.session.add(new_object)


def delete_highlight(timestamp, highlight_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type(timestamp)
	highlight = db.session.query(HighlightsCreated).filter(
								 HighlightsCreated.highlight_ds_id == highlight_ds_id).first()
	if not highlight:
		logger.info('Highlight never created (%s)', highlight_ds_id)
		return
	highlight.deleted = timestamp
	highlight.highlight_ds_id = None


def _bookmark_exists(db, bookmark_ds_id):
	return db.session.query(BookmarksCreated).filter(
							BookmarksCreated.bookmark_ds_id == bookmark_ds_id).count()


def create_bookmark(user, nti_session, bookmark):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	sid = nti_session
	rid = get_ntiid_id(bookmark.containerId)
	rid = get_resource_id(db, rid, create=True)

	bookmark_ds_id = get_ds_id(bookmark)

	if _bookmark_exists(db, bookmark_ds_id):
		logger.warn('Bookmark already exists (ds_id=%s) (user=%s)',
					bookmark_ds_id, user)
		return

	course = get_root_context(bookmark)
	root_context_record = get_root_context_record(db, course, create=True)
	timestamp = get_created_timestamp(bookmark)

	new_object = BookmarksCreated(	session_id=sid,
									timestamp=timestamp,
									bookmark_ds_id=bookmark_ds_id,
									resource_id=rid)
	new_object._user_record = user_record
	new_object._root_context_record = root_context_record
	db.session.add(new_object)


def delete_bookmark(timestamp, bookmark_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type(timestamp)
	bookmark = db.session.query(BookmarksCreated).filter(
								BookmarksCreated.bookmark_ds_id == bookmark_ds_id).first()
	if not bookmark:
		logger.info('Bookmark never created (%s)', bookmark_ds_id)
		return
	bookmark.deleted = timestamp
	bookmark.bookmark_ds_id = None


def _get_note_from_db_id(note_id):
	"""
	Return the actual note object represented by the given db id.
	"""
	db = get_analytics_db()
	note = db.session.query(NotesCreated).filter(
							NotesCreated.note_id == note_id).first()
	note = get_ds_object(note.note_ds_id)
	return note


def _resolve_note(row, user=None, course=None, parent_user=None):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	if parent_user is not None:
		row.RepliedToUser = parent_user
	return row


def get_notes(user=None, course=None, get_deleted=False, replies_only=False, top_level_only=False, **kwargs):
	"""
	Fetch any notes for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted, or whether the note is top-level.
	"""
	filters = []
	if not get_deleted:
		filters.append(NotesCreated.deleted == None)

	if replies_only and top_level_only:
		return ()

	if top_level_only:
		filters.append(NotesCreated.parent_id == None)

	results = get_filtered_records(	user, NotesCreated, course=course,
									replies_only=replies_only, filters=filters, **kwargs)
	return resolve_objects(_resolve_note, results, user=user, course=course)


def _resolve_note_view(row, note=None, user=None, course=None):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	if note is not None:
		row.Note = note
	return row


def get_note_views(user=None, note=None, course=None, **kwargs):
	filters = []
	if note is not None:
		db = get_analytics_db()
		note_ds_id = get_ds_id(note)
		note_id = _get_note_id(db, note_ds_id)
		filters.append(NotesViewed.note_id == note_id)

	results = get_filtered_records(	user, NotesViewed, course=course,
									filters=filters, **kwargs)
	return resolve_objects(_resolve_note_view, results, note=note, user=user, course=course)


def get_note_last_view( note, user ):
	db = get_analytics_db()
	note_ds_id = get_ds_id(note)
	note_id = _get_note_id(db, note_ds_id)
	user_id = get_user_db_id( user )
	result = db.session.query( func.max( NotesViewed.timestamp )  ).filter(
										NotesViewed.note_id == note_id,
										NotesViewed.user_id == user_id ).one()
	return result and result[0]


def get_likes_for_users_notes(user, course=None, **kwargs):
	"""
	Fetch any likes created for a user's notes *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects(NoteLikes, user, course=course, **kwargs)
	return resolve_objects(resolve_like, results, obj_creator=user)


def get_favorites_for_users_notes(user, course=None, **kwargs):
	"""
	Fetch any favorites created for a user's notes *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects(NoteFavorites, user, course=course, **kwargs)
	return resolve_objects(resolve_favorite, results, obj_creator=user)


def get_user_replies_to_others(user, course=None, **kwargs):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	results = _get_user_replies_to_others(NotesCreated, user, course, **kwargs)
	return resolve_objects(_resolve_note, results, user=user, course=course)


def get_replies_to_user(user, course=None, **kwargs):
	"""
	Fetch any replies to our user, *after* the optionally given timestamp.
	"""
	results = _get_replies_to_user(NotesCreated, user, course, **kwargs)
	return resolve_objects(_resolve_note, results, course=course, parent_user=user)


def _resolve_highlight(row, user=None, course=None):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	return row


def get_highlights(user=None, course=None, get_deleted=False, **kwargs):
	"""
	Fetch any highlights for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	filters = ()
	if not get_deleted:
		filters = (HighlightsCreated.deleted == None,)
	results = get_filtered_records(user, HighlightsCreated, course=course,
								filters=filters, **kwargs)
	return resolve_objects(_resolve_highlight, results, user=user, course=course)


def get_highlights_created_for_course(course):
	return get_highlights(course=course)


def _resolve_bookmark(row, user=None, course=None):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	return row


def get_bookmarks(user, course=None, get_deleted=False, **kwargs):
	"""
	Fetch any bookmarks for a user started *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	filters = ()
	if not get_deleted:
		filters = (BookmarksCreated.deleted == None,)
	results = get_filtered_records(	user, BookmarksCreated, course=course,
									filters=filters, **kwargs)
	return resolve_objects(_resolve_bookmark, results, user=user, course=course)
