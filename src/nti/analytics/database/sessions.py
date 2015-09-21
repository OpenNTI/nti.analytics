#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from geoip import geolite2
from geopy import geocoders

from sqlalchemy import Float
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey

from sqlalchemy.orm.session import make_transient
from sqlalchemy.schema import Sequence

from nti.analytics.common import timestamp_type

from nti.analytics.read_models import AnalyticsSession

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import SESSION_COLUMN_TYPE

from nti.analytics.database.users import get_or_create_user

from nti.analytics.database._utils import get_filtered_records

from . import resolve_objects

class Sessions(Base):
	__tablename__ = 'Sessions'
	session_id = Column('session_id', SESSION_COLUMN_TYPE, Sequence('session_id_seq'), index=True, primary_key=True)
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False)
	ip_addr = Column('ip_addr', String(64))
	user_agent_id = Column('user_agent_id', Integer)
	start_time = Column('start_time', DateTime)
	end_time = Column('end_time', DateTime)

class IpGeoLocation(Base):
	# FIXME: Since there is a table dedicated to storing locations, it would
	# make sense to rename this table to IpLocation or something similar, to
	# indicate that this table stores a list of distinct IPs, but not their
	# geographical locations.
	__tablename__ = 'IpGeoLocation'

	# Store ip_addr and country code, with lat/long.
	# We can use 'geopy.geocoders' to lookup state/postal_code data
	# from lat/long.  It may make sense to gather this information at
	# read time.
	# Store by user_id for ease of lookup.
	ip_id = Column('ip_id', Integer, Sequence('ip_id_seq'), index=True, primary_key=True)
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=False)
	ip_addr = Column('ip_addr', String(64), index=True)
	country_code = Column('country_code', String(8))
	latitude = Column('latitude', Float())
	longitude = Column('longitude', Float())
	location_id = Column('location_id', Integer, nullable=True, index=True)

class Location(Base):
	__tablename__ = 'Location'

	# Stores a list of distinct locations of users,
	# by lat/long coordinates.
	# Each location has a unique ID.
	location_id = Column('location_id', Integer, Sequence('location_id_seq'), primary_key=True)
	latitude = Column('latitude', String(64))
	longitude = Column('longitude', String(64))
	city = Column('city', String(64))
	state = Column('state', String(64))
	country = Column('country', String(64))

class UserAgents(Base):
	__tablename__ = 'UserAgents'
	user_agent_id = Column('user_agent_id', Integer, Sequence('user_agent_id_seq'), index=True, primary_key=True)
	# Indexing this large column could be fairly expensive.  Does it get us anything,
	# or should we rely on a full column scan before inserting (perhaps also expensive)?
	# Another alternative would be to hash this value in another column and just check that.
	# If we do so, would we have to worry about collisions between unequal user-agents?
	user_agent = Column('user_agent', String(512), unique=True, index=True, nullable=False)

def _create_user_agent(db, user_agent):
	new_agent = UserAgents(user_agent=user_agent)
	db.session.add(new_agent)
	db.session.flush()
	return new_agent

def _get_user_agent_id(db, user_agent):
	user_agent_record = db.session.query(UserAgents).filter(
										UserAgents.user_agent == user_agent).first()
	if user_agent_record is None:
		user_agent_record = _create_user_agent(db, user_agent)
	return user_agent_record.user_agent_id

def _get_user_agent(user_agent):
	# We have a 512 limit on user agent, truncate if we have to.
	return user_agent[:512] if len(user_agent) > 512 else user_agent

def end_session(user, session_id, timestamp):
	timestamp = timestamp_type(timestamp)
	db = get_analytics_db()

	# Make sure to verify the user/session match up; if possible.
	if user is not None:
		user = get_or_create_user(user)
		uid = user.user_id

		old_session = db.session.query(Sessions).filter(
										Sessions.session_id == session_id,
										Sessions.user_id == uid).first()
	else:
		old_session = db.session.query(Sessions).filter(
										Sessions.session_id == session_id).first()

	result = None

	# Make sure we don't end a session that was already explicitly
	# ended.
	if 		old_session is not None \
		and not old_session.end_time:
		old_session.end_time = timestamp
		result = old_session
	return result

def _create_ip_location(db, ip_addr, user_id):
	ip_info = geolite2.lookup(ip_addr)
	# In one case, we had ip_info but no lat/long.
	if ip_info and ip_info.location and len(ip_info.location) > 1:
		ip_location = IpGeoLocation(ip_addr=ip_addr,
									user_id=user_id,
 									country_code=ip_info.country)
		db.session.add(ip_location)
		db.session.flush()
		# We truncate location coordinates to 4 decimal places
		# and converting to strings. This way we have a consistent
		# level of precision, and comparing as strings instead of
		# floats ensures the accuracy of comparisons. Everything is
		# stored as strings except if we need to do a lookup,
		# in which case they are converted to floats for the lookup
		ip_location.location_id = _get_location_id(	db,
													str(round(ip_info.location[0], 4)),
													str(round(ip_info.location[1], 4)))
		db.session.flush()

def _check_ip_location(db, ip_addr, user_id):
	# Should only be null in tests.
	if ip_addr:
		old_ip_location = db.session.query(IpGeoLocation).filter(
										IpGeoLocation.ip_addr == ip_addr,
										IpGeoLocation.user_id == user_id).first()
		if not old_ip_location:
			# This is a new IP location
			_create_ip_location(db, ip_addr, user_id)

		else:
			old_location_data = db.session.query(Location).filter(
												Location.location_id == old_ip_location.location_id).first()
			old_ip_location.location_id = _get_location_id(	db,
															old_location_data.latitude,
															old_location_data.longitude)

def _get_location_id(db, lat_str, long_str):

	existing_location = db.session.query(Location).filter(Location.latitude == lat_str,
														  Location.longitude == long_str).first()

	if not existing_location:
		# We've never seen this location before, so create
		# a new row for it in the Location table and return location_id
		new_location = _create_new_location(db, lat_str, long_str)
		return new_location.location_id

	else:
		# This Location already exists, so make sure its fields are all
		# filled out if possible, then return its location_id
		if 		existing_location.city == '' \
			and existing_location.state == '' \
			and existing_location.country == '':
			_create_new_location(db, lat_str, long_str, existing_location)
		return existing_location.location_id

def _lookup_location(lat, long_):
	# Using Nominatim as our lookup service for now, because
	# they don't require registration or an API key. The downside
	# is that they have a usage limit of 1 lookup/second.
	# See http://wiki.openstreetmap.org/wiki/Nominatim_usage_policy
	# for more details on the usage policy.

	def _encode(val):
		try:
			return str(val) if val else u''
		except Exception:
			return u''

	try:
		geolocator = geocoders.Nominatim()
		location = geolocator.reverse((lat, long_))
		location_address = location.raw.get('address')
		_city = _encode(location_address.get('city'))
		_state = _encode(location_address.get('state'))
		_country = _encode(location_address.get('country'))
	except:
		logger.info('Reverse geolookup for %s, %s failed.' % (lat, long_))
		_city = _state = _country = ''
	return (_city, _state, _country)

def _create_new_location(db, lat_str, long_str, existing_location=None):
	# Returns the location_id of the row created in the Location table

	lat = float(lat_str)
	long_ = float(long_str)

	# Try to look up the location and add it as a new location.
	# If the lookup fails for any reason, just add the location
	# without the names of city, state, and country

	try:
		_city, _state, _country = _lookup_location(lat, long_)
	except:
		logger.info('Reverse geolookup for %s, %s failed.' % (lat, long_))
		_city = _state = _country = u''

	# If we got an existing location, update the data
	# instead of creating a new location
	if existing_location:
		existing_location.city = _city
		existing_location.state = _state
		existing_location.country = _country
		return existing_location
	else:
		new_location = Location(latitude=lat_str, longitude=long_str, 
								city=_city, state=_state, country=_country)
		db.session.add(new_location)
		# need to flush here so that our new location will be assigned a location_id
		db.session.flush()
		return new_location

def create_session(user, user_agent, start_time, ip_addr, end_time=None):
	db = get_analytics_db()
	user = get_or_create_user(user)
	uid = user.user_id
	start_time = timestamp_type(start_time)
	end_time = timestamp_type(end_time) if end_time is not None else None
	user_agent = _get_user_agent(user_agent)
	user_agent_id = _get_user_agent_id(db, user_agent)

	new_session = Sessions(	user_id=uid,
							start_time=start_time,
							end_time=end_time,
							ip_addr=ip_addr,
							user_agent_id=user_agent_id)

	_check_ip_location(db, ip_addr, uid)

	db.session.add(new_session)
	db.session.flush()

	make_transient(new_session)
	return new_session

def get_session_by_id(session_id):
	db = get_analytics_db()
	session_record = db.session.query(Sessions).filter(
									Sessions.session_id == session_id).first()
	if session_record:
		make_transient(session_record)
	return session_record

def _resolve_session(row):
	make_transient(row)
	duration = None
	if row.end_time:
		duration = row.end_time - row.start_time
		duration = duration.seconds

	result = AnalyticsSession(SessionID=row.session_id,
							  SessionStartTime=row.start_time,
							  SessionEndTime=row.end_time,
							  Duration=duration)
	return result

def get_user_sessions(user, timestamp=None, max_timestamp=None):
	"""
	Fetch any sessions for a user started *after* the optionally given timestamp.
	"""
	filters = []
	if timestamp is not None:
		filters.append(Sessions.start_time >= timestamp,)

	if max_timestamp is not None:
		filters.append(Sessions.start_time <= max_timestamp)

	results = get_filtered_records(user, Sessions, filters=filters)
	return resolve_objects(_resolve_session, results)
