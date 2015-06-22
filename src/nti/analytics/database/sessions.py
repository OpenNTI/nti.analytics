#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from geoip import geolite2

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime

from sqlalchemy.orm.session import make_transient
from sqlalchemy.schema import Sequence

from nti.analytics.common import timestamp_type

from nti.analytics.read_models import AnalyticsSession

from nti.analytics.database import SESSION_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.users import get_or_create_user

from nti.analytics.database._utils import get_filtered_records

from . import resolve_objects

class Sessions(Base):
	__tablename__ = 'Sessions'
	session_id = Column('session_id', SESSION_COLUMN_TYPE, Sequence('session_id_seq'), index=True, primary_key=True )
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False )
	ip_addr = Column('ip_addr', String(64))
	user_agent_id = Column('user_agent_id', Integer)
	start_time = Column('start_time', DateTime)
	end_time = Column('end_time', DateTime)

class IpGeoLocation(Base):
	__tablename__ = 'IpGeoLocation'

	# Store ip_addr and country code, with lat/long.
	# We can use 'geopy.geocoders' to lookup state/postal_code data
	# from lat/long.  It may make sense to gather this information at
	# read time.
	# Store by user_id for ease of lookup.
	ip_id = Column('ip_id', Integer, Sequence('ip_id_seq'), index=True, primary_key=True )
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False )
	ip_addr = Column('ip_addr', String(64), index=True)
	country_code = Column('country_code', String(8))
	latitude = Column( 'latitude', Float() )
	longitude = Column( 'longitude', Float() )

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
	user_agent_record = db.session.query(UserAgents).filter(
										UserAgents.user_agent == user_agent ).first()
	if user_agent_record is None:
		user_agent_record = _create_user_agent( db, user_agent )
	return user_agent_record.user_agent_id

def _get_user_agent( user_agent ):
	# We have a 512 limit on user agent, truncate if we have to.
	return user_agent[:512] if len( user_agent ) > 512 else user_agent

def end_session( user, session_id, timestamp ):
	timestamp = timestamp_type( timestamp )
	db = get_analytics_db()

	# Make sure to verify the user/session match up; if possible.
	if user is not None:
		user = get_or_create_user( user )
		uid = user.user_id

		old_session = db.session.query( Sessions ).filter(
										Sessions.session_id == session_id,
										Sessions.user_id == uid ).first()
	else:
		old_session = db.session.query( Sessions ).filter(
										Sessions.session_id == session_id).first()

	result = None

	# Make sure we don't end a session that was already explicitly
	# ended.
	if 		old_session is not None \
		and not old_session.end_time:
		old_session.end_time = timestamp
		result = old_session
	return result

def _create_ip_location( db, ip_addr, user_id ):
	ip_info = geolite2.lookup( ip_addr )
	# In one case, we had ip_info but no lat/long.
	if ip_info and ip_info.location and len( ip_info.location ) > 1:
		ip_location = IpGeoLocation( ip_addr=ip_addr,
									user_id=user_id,
 									country_code=ip_info.country,
									latitude=ip_info.location[0],
									longitude=ip_info.location[1] )
		db.session.add( ip_location )

def _check_ip_location( db, ip_addr, user_id ):
	# Should only be null in tests.
	if ip_addr:
		old_ip_location = db.session.query( IpGeoLocation ).filter(
										IpGeoLocation.ip_addr == ip_addr,
										IpGeoLocation.user_id == user_id ).first()
		if not old_ip_location:
			_create_ip_location( db, ip_addr, user_id )

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

	_check_ip_location( db, ip_addr, uid )

	db.session.add( new_session )
	db.session.flush()

	make_transient( new_session )
	return new_session

def get_session_by_id( session_id ):
	db = get_analytics_db()
	session_record = db.session.query( Sessions ).filter(
									Sessions.session_id == session_id ).first()
	if session_record:
		make_transient( session_record )
	return session_record

def _resolve_session( row ):
	make_transient( row )
	duration = None
	if row.end_time:
		duration = row.end_time - row.start_time
		duration = duration.seconds

	result = AnalyticsSession( SessionID=row.session_id,
							SessionStartTime=row.start_time,
							SessionEndTime=row.end_time,
							Duration=duration )
	return result

def get_user_sessions( user, timestamp=None ):
	"""
	Fetch any sessions for a user started *after* the optionally given timestamp.
	"""
	filters = ()
	if timestamp is not None:
		filters = ( Sessions.start_time >= timestamp, )
	results = get_filtered_records( user, Sessions, filters=filters )
	return resolve_objects( _resolve_session, results )
