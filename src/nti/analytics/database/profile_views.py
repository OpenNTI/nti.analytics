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

from sqlalchemy.schema import PrimaryKeyConstraint

from sqlalchemy.ext.declarative import declared_attr

from nti.analytics.common import get_entity
from nti.analytics.common import timestamp_type

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

from nti.analytics.database.users import get_or_create_user

from nti.analytics.database._utils import get_context_path

from nti.analytics.identifier import SessionId

class EntityProfileMixin(BaseViewMixin, TimeLengthMixin):

	@declared_attr
	def target_id(cls):
		return Column('target_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False)

class EntityProfileViews(Base,EntityProfileMixin):
	__tablename__ = 'EntityProfileViews'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'target_id', 'timestamp'),
    )

class EntityProfileActivityViews(Base,EntityProfileMixin):
	__tablename__ = 'EntityProfileActivityViews'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'target_id', 'timestamp'),
    )

class EntityProfileMembershipViews(Base,EntityProfileMixin):
	__tablename__ = 'EntityProfileMembershipViews'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'target_id', 'timestamp'),
    )

def _profile_view_exists( db, table, user_id, target_id, timestamp ):
	return db.session.query( table ).filter(
							table.user_id == user_id,
							table.target_id == target_id,
							table.timestamp == timestamp ).first()

def _create_profile_view( event, table, nti_session ):
	db = get_analytics_db()
	user = get_entity( event.user )
	user = get_or_create_user( user )
	user_id = user.user_id

	target = get_entity( event.ProfileEntity )
	target = get_or_create_user( target )
	target_id = target.user_id

	timestamp = timestamp_type( event.timestamp )
	context_path = get_context_path( event.context_path )

	existing_record = _profile_view_exists( db, table, user_id, target_id, timestamp )
	time_length = event.time_length

	sid = SessionId.get_id( nti_session )

	if existing_record is not None:
		if should_update_event( existing_record, time_length ):
			existing_record.time_length = time_length
		return

	view_record = table( user_id=user_id,
						session_id=sid,
						target_id=target_id,
						timestamp=timestamp,
						context_path=context_path,
						time_length=time_length )
	db.session.add( view_record )
	logger.debug( 'Profile view event (user=%s) (target=%s)', event.user, event.ProfileEntity )

def create_profile_view( event, nti_session ):
	_create_profile_view( event, EntityProfileViews, nti_session )

def create_profile_activity_view( event, nti_session ):
	_create_profile_view( event, EntityProfileActivityViews, nti_session )

def create_profile_membership_view( event, nti_session ):
	_create_profile_view( event, EntityProfileMembershipViews, nti_session )
