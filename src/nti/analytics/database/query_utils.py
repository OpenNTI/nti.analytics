#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics.database import get_analytics_db

from nti.analytics.database.root_context import get_root_context_id

from nti.analytics.database.users import get_user_db_id

from nti.contenttypes.courses.interfaces import ICourseSubInstance

_yield_all_marker = object()

def _do_course_and_timestamp_filtering(table, timestamp=None, max_timestamp=None,
									   course=None, filters=None, query_builder=None,
									   yield_per=_yield_all_marker, limit=None, order_by=None):
	db = get_analytics_db()
	result = []

	if filters is None:
		filters = []

	if course is not None:
		course_id = get_root_context_id(db, course)
		course_ids = [ course_id ]

		# XXX: For courses with super-instances (e.g. History)
		# we want to aggregate any data that may have been
		# pinned on the super instance as well. I think we
		# would want this for any scenario.
		if ICourseSubInstance.providedBy(course):
			parent = course.__parent__.__parent__
			parent_id = get_root_context_id(db, parent)
			course_ids.append(parent_id)

		if course_ids:
			filters.append(table.course_id.in_(course_ids))
		else:
			# If we have a course, but no course_id (return empty)
			return result

	if timestamp is not None:
		filters.append(table.timestamp >= timestamp)

	if max_timestamp is not None:
		filters.append(table.timestamp <= max_timestamp)

	query = db.session.query(table).filter(*filters)

	order_by = getattr(table, order_by, None) if order_by else None
	if order_by:
		query = query.order_by(order_by.desc())

	if limit:
		query = query.limit(limit)

	if query_builder:
		query = query_builder(query)

	if yield_per is _yield_all_marker:
		result = query.all()
	elif yield_per > 0:
		result = query.yield_per(yield_per).enable_eagerloads(False)
	else:
		result = query
	return result

def get_filtered_records(user, table, replies_only=False, filters=None, **kwargs):
	"""
	Get the filtered records for the given user, table, timestamp (and course).
	"""
	result = []
	filters = list(filters) if filters else []

	if user is not None:
		user_id = get_user_db_id(user)
		if user_id is not None:
			filters.append(table.user_id == user_id)
		else:
			# If we have a user, but no user_id (return empty)
			return result

	if replies_only:
		filters.append(table.parent_user_id != None)

	result = _do_course_and_timestamp_filtering(table, filters=filters, **kwargs)
	return result

def get_user_replies_to_others(table, user, get_deleted=False, filters=None, **kwargs):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	user_id = get_user_db_id(user)

	filters = [] if filters is None else list(filters)
	filters.append(table.parent_user_id != user_id)

	if not get_deleted:
		filters.append(table.deleted == None)

	result = get_filtered_records(user, table, filters=filters, **kwargs)
	return result

def get_replies_to_user(table, user, get_deleted=False, **kwargs):
	"""
	Fetch any replies to our user, *after* the optionally given timestamp.
	"""
	# This is similar to our generic filtering func above, but
	# we want to specifically exclude our given user.
	result = []
	user_id = get_user_db_id(user)
	filters = [ table.parent_user_id == user_id,
				table.user_id != user_id ]

	if not get_deleted:
		filters.append(table.deleted == None)

	if user_id is not None:
		result = _do_course_and_timestamp_filtering(table, filters=filters, **kwargs)

	return result

def get_ratings_for_user_objects(table, user, **kwargs):
	"""
	Fetch any ratings for a user's objects, optionally filtering by date,
	course.
	"""
	# This is similar to our generic filtering func above, but
	# we want to specifically exclude our given user.
	result = []
	user_id = get_user_db_id(user)
	# Do we want to exclude any self-favorites/likes?
	filters = [ table.creator_id == user_id ]

	if user_id is not None:
		result = _do_course_and_timestamp_filtering(table, filters=filters, **kwargs)

	return result

def _do_resolve_rating(row, rater, obj_creator):
	if rater is not None:
		row.user = rater
	if obj_creator is not None:
		row.Creator = obj_creator
	return row

def resolve_like(row, rater=None, obj_creator=None):
	return _do_resolve_rating(row, rater, obj_creator)

def resolve_favorite(row, rater=None, obj_creator=None):
	return _do_resolve_rating(row, rater, obj_creator)
