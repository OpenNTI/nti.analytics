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

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import UserId
from nti.analytics.identifier import SessionId
_userid = UserId()
_sessionid = SessionId()

from nti.analytics.database import SESSION_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

class Users(Base):
	__tablename__ = 'Users'
	# Sequence must be primary key, even though we'd like to not do so (for merge purposes).
	user_id = Column('user_id', Integer, Sequence('user_id_seq'), index=True, nullable=False, primary_key=True )
	user_ds_id = Column('user_ds_id', Integer, nullable=False, unique=True, index=True )
	shareable = Column('shareable', Boolean, nullable=False, default=False )

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

	user = Users( user_ds_id=uid )
	# We'd like to use 'merge' here, but we cannot (in sqlite) if our primary key
	# is a sequence.
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
