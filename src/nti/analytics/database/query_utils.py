#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics.database import get_analytics_db

from nti.analytics.database.root_context import get_root_context_id

from nti.analytics.database.users import get_user_db_id

from nti.contenttypes.courses.interfaces import ICourseSubInstance

logger = __import__('logging').getLogger(__name__)

_yield_all_marker = object()


def _query_factory(session, table):
	return session.query(table)


def _do_context_and_timestamp_filtering(table,
									    timestamp=None,
                                        max_timestamp=None,
									    course=None,
									    root_context=None,
									    filters=None,
									    query_builder=None,
									    yield_per=_yield_all_marker,
									    limit=None,
									    order_by=None,
									    query_factory=_query_factory):
	"""
	A helper func that will build a query (and possibly executing), filtering o
	n various params.

	`root_context` and `course` are treated as synonyms for now.

	:param table: The table the query will run on
	:param DateTime timestamp: The minimum DateTime value
	:param DateTime max_timestamp: The maximum DateTime value
	:param course: The course_id to filter on
	:param root_context: The root_context to filter on. May be a book or course.
	:param filters: Existing sqlalchemy filters to apply.
	"""
	db = get_analytics_db()
	result = []

	if filters is None:
		filters = []

	if course is not None or root_context is not None:
		if root_context is None:
			root_context = course
		context_id = get_root_context_id(db, root_context)
		context_ids = [context_id]

		# XXX: For courses with super-instances (e.g. History) we want to
		# aggregate any data that may have been pinned on the super instance
		# as well. I think we would want this for any scenario.
		if ICourseSubInstance.providedBy(root_context):
			parent = root_context.__parent__.__parent__
			parent_id = get_root_context_id(db, parent)
			context_ids.append(parent_id)

		if context_ids:
			# TODO: Make this explicit; queries for courses query for
			# `course_id` and those that are agnostic query for
			# `root_context_id`.
			try:
				filters.append(table.root_context_id.in_(context_ids))
			except AttributeError:
				filters.append(table.course_id.in_(context_ids))
		else:
			# If we have a course, but no course_id (return empty)
			return result

	if timestamp is not None:
		filters.append(table.timestamp >= timestamp)

	if max_timestamp is not None:
		filters.append(table.timestamp <= max_timestamp)

	query = query_factory(db.session, table).filter(*filters)

	if order_by is not None:
		order_by = getattr(table, order_by, order_by)
		if hasattr(order_by, 'desc'):
			order_by = order_by.desc()
		if order_by is not None:
			query = query.order_by(order_by)

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

	result = _do_context_and_timestamp_filtering(table, filters=filters, **kwargs)
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
		result = _do_context_and_timestamp_filtering(table, filters=filters, **kwargs)

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
		result = _do_context_and_timestamp_filtering(table, filters=filters, **kwargs)

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
