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
from sqlalchemy import DateTime

from sqlalchemy.schema import Sequence

import zope.intid

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
_sessionid = SessionId()

from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import SESSION_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.users import get_or_create_user

class Sessions(Base):
	__tablename__ = 'Sessions'
	session_id = Column('session_id', SESSION_COLUMN_TYPE, Sequence('session_id_seq'), index=True, primary_key=True )
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False )
	ip_addr = Column('ip_addr', String(64))
	platform = Column('platform', String(256))
	start_time = Column('start_time', DateTime)
	end_time = Column('end_time', DateTime)

class CurrentSessions(Base):
	__tablename__ = 'CurrentSessions'
	session_id = Column('session_id', SESSION_COLUMN_TYPE, ForeignKey('Sessions.session_id'), index=True, primary_key=True )
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False )

def _update_current_session( db, new_session, uid ):
	# Wipe old sessions, add our new one.
	old_sessions = db.session.query( CurrentSessions ).filter( CurrentSessions.user_id == uid ).delete()
	new_current_session = CurrentSessions( user_id=uid, session_id=new_session.session_id )
	db.session.add( new_current_session )

def create_session( user, platform, timestamp, ip_addr ):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	timestamp = timestamp_type( timestamp )

	new_session = Sessions( user_id=uid,
							start_time=timestamp,
							ip_addr=ip_addr,
							platform=platform )
	db.session.add( new_session )
	db.session.flush()

	_update_current_session( db, new_session, uid )

def get_current_session_id( user ):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	current_session = db.session.query( CurrentSessions ).filter( CurrentSessions.user_id == uid ).first()
	result = None
	if current_session is not None:
		result = current_session.session_id
	return result
