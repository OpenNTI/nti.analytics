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
from sqlalchemy import ForeignKey
from sqlalchemy import Boolean
from sqlalchemy import DateTime

from sqlalchemy.schema import Sequence

import zope.intid

from nti.app.products.ou.interfaces import IUserResearchStatus

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import UserId
from nti.analytics.identifier import SessionId
_userid = UserId()
_sessionid = SessionId()

from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import SESSION_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

class Users(Base):
	__tablename__ = 'Users'
	user_id = Column('user_id', Integer, Sequence('user_id_seq'), index=True, nullable=False, primary_key=True )
	user_ds_id = Column('user_ds_id', INTID_COLUMN_TYPE, nullable=True, index=True )
	allow_research = Column('allow_research', Boolean, nullable=True, default=None )
	username = Column('username', String(64), nullable=True, unique=False, index=True)

class Sessions(Base):
	__tablename__ = 'Sessions'
	session_id = Column('session_id', SESSION_COLUMN_TYPE, primary_key=True )
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), nullable=False )
	ip_addr = Column('ip_addr', String(64))
	platform = Column('platform', String(64))
	version = Column('version', String(64))
	start_time = Column('start_time', DateTime)
	end_time = Column('end_time', DateTime)


def create_user(user):
	db = get_analytics_db()
	# We may have non-IUsers here, but let's keep them since we may need
	# them (e.g. community owned forums).
	username = getattr( user, 'username', None )
	uid = _userid.get_id( user )

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
	uid = _userid.get_id( user )
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

def create_session(user, session_id, timestamp, ip_address, platform, version):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	timestamp = timestamp_type( timestamp )

	new_session = Sessions( user_id=uid,
							session_id=session_id,
							start_time=timestamp,
							ip_addr=ip_address,
							platform=platform,
							version=version )
	db.session.add( new_session )

def end_session(session_id, timestamp):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	nti_session = db.session.query(Sessions).filter( Sessions.session_id == session_id ).first()
	if nti_session:
		nti_session.end_time = timestamp
	else:
		# This could happen during the initial startup phase, be forgiving.
		logger.debug( 'Session ending but no record found in Sessions table (sid=%s)', session_id )
