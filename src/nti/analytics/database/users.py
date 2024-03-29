#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.analytics_database.users import Users

from nti.analytics.common import get_created_timestamp

from nti.analytics.database import get_analytics_db

from nti.analytics.identifier import get_ds_id
from nti.analytics.identifier import get_ds_object

from nti.analytics.interfaces import IUserResearchStatus

from nti.dataserver.interfaces import IUsernameSubstitutionPolicy

logger = __import__('logging').getLogger(__name__)


def _get_username2(user):
	"""
	Return the applicable alternate username, if we have a policy for it.
	"""
	username = getattr(user, 'username', None) or ''
	policy = component.queryUtility(IUsernameSubstitutionPolicy)
	result = policy.replace(username) if policy is not None else ''
	if username == result:
		result = ''
	return result


def create_user(user):
	db = get_analytics_db()
	# We may have non-IUsers here, but let's keep them since we may need
	# them (e.g. community owned forums).
	username = getattr(user, 'username', None)
	uid = get_ds_id(user)

	allow_research = None
	user_research = IUserResearchStatus(user, None)
	if user_research is not None:
		allow_research = user_research.allow_research

	username2 = _get_username2(user) or username
	create_date = get_created_timestamp(user)

	user = Users(user_ds_id=uid,
				 allow_research=allow_research,
				 username=username,
				 username2=username2,
				 create_date=create_date)

	# For race conditions, let's just throw since we cannot really handle retrying
	# gracefully at this level. A job-level retry should work though.
	db.session.add(user)
	logger.info('Created user (user=%s) (user_id=%s) (user_ds_id=%s)',
				username, user.user_id, uid)
	return user


def get_user_record(user):
	# Look into using sqlalchemy baked queries for this
	# and other high volume calls that return a single row.
	# This is still considered experimental for 1.0.0.
	if isinstance(user, Users):
		return user
	db = get_analytics_db()
	uid = get_ds_id(user)
	found_user = db.session.query(Users).filter(Users.user_ds_id == uid).first()
	return found_user


def get_or_create_user(user):
	found_user = get_user_record(user)
	if found_user is not None:
		# Lazy build fields.
		# This can only be called on POSTs.
		if found_user.username2 is None:
			found_user.username2 = _get_username2(user)
		if found_user.create_date is None:
			found_user.create_date = get_created_timestamp(user)

	return found_user or create_user(user)


def get_user_db_id(user):
	found_user = get_user_record(user)
	return found_user and found_user.user_id


def get_user(user_id):
	"""
	Retrieves user with given db id.
	"""
	result = None
	db = get_analytics_db()
	found_user = db.session.query(Users).filter(Users.user_id == user_id,
												Users.user_ds_id != None).first()
	if found_user is not None:
		result = get_ds_object(found_user.user_ds_id)

	return result


def delete_entity(entity_ds_id):
	db = get_analytics_db()
	found_user = db.session.query(Users).filter(
								  Users.user_ds_id == entity_ds_id).first()
	if found_user is not None:
		found_user.user_ds_id = None


def update_user_research(user_ds_id, allow_research):
	db = get_analytics_db()
	found_user = db.session.query(Users).filter(
								  Users.user_ds_id == user_ds_id).first()
	if found_user is not None:
		found_user.allow_research = allow_research

