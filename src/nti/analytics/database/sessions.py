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

from sqlalchemy.orm.session import make_transient
from sqlalchemy.schema import Sequence

from nti.analytics.common import timestamp_type

from nti.analytics.database import SESSION_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database.users import get_or_create_user

class Sessions(Base):
	__tablename__ = 'Sessions'
	session_id = Column('session_id', SESSION_COLUMN_TYPE, Sequence('session_id_seq'), index=True, primary_key=True )
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False )
	ip_addr = Column('ip_addr', String(64))
	user_agent_id = Column('user_agent_id', Integer)
	start_time = Column('start_time', DateTime)
	end_time = Column('end_time', DateTime)

class CurrentSessions(Base):
	__tablename__ = 'CurrentSessions'
	session_id = Column('session_id', SESSION_COLUMN_TYPE, ForeignKey('Sessions.session_id'), index=True, primary_key=True )
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False )

class UserAgents(Base):
	__tablename__ = 'UserAgents'
	user_agent_id = Column('user_agent_id', Integer, Sequence('user_agent_id_seq'), index=True, primary_key=True )
	# Indexing this large column could be fairly expensive.  Does it get us anything,
	# or should we rely on a full column scan before inserting (perhaps also expensive)?
	# Another alternative would be to hash this value in another column and just check that.
	# If we do so, would we have to worry about collisions between unequal user-agents?
	user_agent = Column('user_agent', String(512), unique=True, index=True, nullable=False )

def _create_user_agent( db, user_agent ):
	new_agent = UserAgents( user_agent=user_agent )
	db.session.add( new_agent )
	db.session.flush()
	return new_agent

def _get_user_agent_id( db, user_agent ):
	user_agent_record = db.session.query(UserAgents).filter( UserAgents.user_agent == user_agent ).first()
	if user_agent_record is None:
		user_agent_record = _create_user_agent( db, user_agent )
	return user_agent_record.user_agent_id

def _update_current_session( db, new_session, uid ):
	# Add our new session.
	new_current_session = CurrentSessions( user_id=uid, session_id=new_session.session_id )
	db.session.add( new_current_session )

def _get_user_agent( user_agent ):
	# We have a 512 limit on user agent, truncate if we have to.
	return user_agent[:512] if len( user_agent ) > 512 else user_agent

def end_session( user, session_id, timestamp ):
	# Make sure to verify the user/session match up.
	user = get_or_create_user( user )
	uid = user.user_id
	timestamp = timestamp_type( timestamp )

	# Empty our current sessions
	db = get_analytics_db()
	db.session.query( CurrentSessions ).filter( CurrentSessions.session_id == session_id,
												CurrentSessions.user_id == uid ).delete()

	old_session = db.session.query( Sessions ).filter( Sessions.session_id == session_id,
														Sessions.user_id == uid ).first()
	if old_session is not None:
		old_session.end_time = timestamp

def create_session( user, user_agent, start_time, ip_addr, end_time=None ):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	start_time = timestamp_type( start_time )
	end_time = timestamp_type( end_time ) if end_time is not None else None
	user_agent = _get_user_agent( user_agent )
	user_agent_id = _get_user_agent_id( db, user_agent )

	new_session = Sessions( user_id=uid,
							start_time=start_time,
							end_time=end_time,
							ip_addr=ip_addr,
							user_agent_id=user_agent_id )
	db.session.add( new_session )
	db.session.flush()

	_update_current_session( db, new_session, uid )
	make_transient( new_session )
	return new_session

def get_current_session_ids( user ):
	"""
	Returns all 'live' sessions for a user.  Primarily used for validation.
	"""
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	all_sessions = db.session.query( CurrentSessions ).filter( CurrentSessions.user_id == uid ).all()
	result = [x.session_id for x in all_sessions]
	return result
