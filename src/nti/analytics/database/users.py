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
from sqlalchemy import String
from sqlalchemy import Boolean

from sqlalchemy.schema import Sequence

from nti.app.products.ou.interfaces import IUserResearchStatus

from nti.analytics.identifier import UserId

from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

class Users(Base):
	__tablename__ = 'Users'
	user_id = Column('user_id', Integer, Sequence('user_id_seq'), index=True, nullable=False, primary_key=True )
	user_ds_id = Column('user_ds_id', INTID_COLUMN_TYPE, nullable=True, index=True )
	allow_research = Column('allow_research', Boolean, nullable=True, default=None )
	username = Column('username', String(64), nullable=True, unique=False, index=True)

def create_user(user):
	db = get_analytics_db()
	# We may have non-IUsers here, but let's keep them since we may need
	# them (e.g. community owned forums).
	username = getattr( user, 'username', None )
	uid = UserId.get_id( user )

	allow_research = None
	# TODO OU specific
	user_research = IUserResearchStatus( user, None )
	if user_research is not None:
		allow_research = user_research.allow_research

	user = Users( 	user_ds_id=uid,
					allow_research=allow_research,
					username=username )
	# For race conditions, let's just throw since we cannot really handle retrying
	# gracefully at this level. A job-level retry should work though.
	db.session.add( user )
	db.session.flush()
	logger.info( 'Created user (user=%s) (user_id=%s) (user_ds_id=%s)', username, user.user_id, uid )
	return user

def get_or_create_user(user):
	db = get_analytics_db()
	uid = UserId.get_id( user )
	found_user = db.session.query(Users).filter( Users.user_ds_id == uid ).first()
	return found_user or create_user( user )

def delete_entity( entity_ds_id ):
	db = get_analytics_db()
	found_user = db.session.query(Users).filter( Users.user_ds_id == entity_ds_id ).first()
	if found_user is not None:
		found_user.user_ds_id = None

def update_user_research( user_ds_id, allow_research ):
	db = get_analytics_db()
	found_user = db.session.query(Users).filter( Users.user_ds_id == user_ds_id ).first()
	if found_user is not None:
		found_user.allow_research = allow_research
