#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Returns a list representation of the geographical
locations of users within a course.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from geoip import geolite2
from geopy import geocoders

from nti.analytics_database.sessions import Location
from nti.analytics_database.sessions import IpGeoLocation

from nti.dataserver.users.users import User
from nti.dataserver.interfaces import IEnumerableEntityContainer

from nti.analytics.database import get_analytics_db

from nti.analytics.database.users import get_user_db_id

ALL_USERS = 'ALL_USERS'


def _get_location_ids_for_users(db, user_ids):
	location_ids = []
	if user_ids:
		location_ids = db.session.query(IpGeoLocation.location_id).filter(
										IpGeoLocation.user_id.in_( user_ids )).all()
		location_ids = (x[0] for x in location_ids)
	return location_ids


def _get_locations_for_ids(db, location_ids, location_counts):
	location_rows = []
	for location_id in location_ids:
		location = db.session.query(Location).filter(
									Location.location_id == location_id).first()
		# count the number of times this location is being used
		if location_id in location_counts:
			location_counts[location_id] += 1
		else:
			# return a list of distinct locations,
			# so only add each location once
			location_rows.append(location)
			location_counts[location_id] = 1
	return location_rows


def _get_location_data(locations, location_counts):
	# Handle everything as unicode. The Google API we're
	# currently using for maps is picky about encoding, but
	# everything is handled internally as unicode. When
	# exporting to the template, we encode everything into
	# UTF-8, and then send that to the template. Javascript
	# converts the UTF-8 strings into the format Google Maps wants.

	def get_user_label(number_of_users):
		if number_of_users > 1:
			return u'%s users' % number_of_users
		else:
			return u'1 user'

	db_data = []

	for location in locations:

		city = location.city
		state = location.state
		country = location.country

		# Create the label for the map marker
		if country == u'United States of America':
			if city and state:
				label = u'%s, %s' % (city, state)
			elif state:
				label = u'%s' % state
			else:
				label = u''
		else:
			if city and country:
				label = u'%s, %s' % (city, country)
			elif country:
				label = u'%s' % country
			else:
				label = u''

		# Add the number of users to the label
		number_of_users_in_location = location_counts[location.location_id]
		label = u'%s (%s)' % (label, get_user_label( number_of_users_in_location ))

		locationData = {
				'latitude': float(location.latitude),
				'longitude': float(location.longitude),
				'label': label,
				'city': city,
				'state': state,
				'country': country,
				'number_of_students': number_of_users_in_location}
		# Append the data for this location as a location element in db_data
		db_data.append(locationData)

	return db_data


def get_location_list(course, enrollment_scope=None):

	db = get_analytics_db()
	location_counts = {}

	user_ids = _get_enrolled_user_ids(course, enrollment_scope)
	location_ids = _get_location_ids_for_users(db, user_ids)
	locations = _get_locations_for_ids(db, location_ids, location_counts)
	data = _get_location_data(locations, location_counts)

	return data


def _get_enrolled_user_ids(course, enrollment_scope=None):
	"""
	Gets a list of the user ids for the specified course and enrollment scope.
	"""
	# Note: this is the same code as in the
	# _get_enrollment_scope_dic method in
	# coursewarereports/views/__init__.py.
	users = _get_enrollment_scope_dict(course)
	user_ids = []
	enrollment_scope = enrollment_scope or ALL_USERS
	usernames_for_scope = users[enrollment_scope]
	for username in usernames_for_scope:
		user = User.get_user(username)
		id_ = get_user_db_id(user)
		if id_ is not None:
			user_ids.append(id_)
	return user_ids


def _get_enrollment_scope_dict(course):

	"""
	Build a dict of scope_name to usernames.
	"""
	# XXX: We are not exposing these multiple scopes in many places,
	# including many reports and in TopCreators.
	# XXX: This is confusing if we are nesting scopes.  Perhaps
	# it makes more sense to keep things in the Credit/NonCredit camps.
	# Seems like it would make sense to have an Everyone scope...
	# { Everyone: { Public : ( Open, Purchased ), ForCredit : ( FCD, FCND ) }}

	# XXX: It's useful here that we're capturing all subinstance students, but
	# that is not messaged to end-user.
	results = {}
	instructors = set( course.instructors )
	# Lumping purchased in with public.
	public_scope = course.SharingScopes.get('Public', None)
	purchased_scope = course.SharingScopes.get('Purchased', None)
	non_public_users = set()
	for scope_name in course.SharingScopes:
		scope = course.SharingScopes.get(scope_name, None)

		if 		scope is not None \
			and scope not in (public_scope, purchased_scope):

			# If our scope is not 'public'-ish, store it separately.
			# All credit-type users should end up in ForCredit.
			scope_users = {x.lower() for x in IEnumerableEntityContainer(scope).iter_usernames()}
			scope_users = scope_users - instructors
			results[scope_name] = scope_users
			non_public_users = non_public_users.union(scope_users)

	all_users = {x.lower() for x in IEnumerableEntityContainer(public_scope).iter_usernames()}
	results['Public'] = all_users - non_public_users - instructors
	results[ALL_USERS] = all_users
	return results


def _lookup_coordinates_for_ip(ip_addr):
	# Given an IP address, lookup and return the coordinates of its location
	return geolite2.lookup(ip_addr)


def _create_ip_location(db, ip_addr, user_id):
	ip_info = _lookup_coordinates_for_ip(ip_addr)
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
		ip_location.location_id = _get_location_id(db,
													str(round(ip_info.location[0], 4)),
													str(round(ip_info.location[1], 4)))
		db.session.flush()


def check_ip_location(db, ip_addr, user_id):
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
			old_ip_location.location_id = _get_location_id(db,
															old_location_data.latitude,
															old_location_data.longitude)

#: To avoid exhausting our service limit.
UPDATE_LIMIT = 500


def update_missing_locations():
	"""
	Cycle through our locations, querying and updating
	any locations with missing data.
	"""
	db = get_analytics_db()
	update_count = 0
	checked_count = 0

	for location in db.session.query( Location ).yield_per( 1000 ):
		if 		not location.city \
			or 	not location.state \
			or 	not location.country:
			checked_count += 1
			_create_new_location( db, location.latitude, location.longitude, location )

			if location.city or location.state:
				update_count += 1
			if checked_count > UPDATE_LIMIT:
				break
	return update_count


def _get_location_id(db, lat_str, long_str):

	existing_location = db.session.query(Location).filter(
										Location.latitude == lat_str,
							 		 	Location.longitude == long_str).first()

	if not existing_location:
		# We've never seen this location before, so create
		# a new row for it in the Location table and return location_id
		new_location = _create_new_location(db, lat_str, long_str)
		return new_location.location_id

	else:
		# This Location already exists, so make sure its fields are all
		# filled out if possible, then return its location_id.
		# We do a lookup if *any* fields are missing to backfill
		# missing foreign locations.  At a later point, we should
		# perhaps only perform a lookup if all fields are empty.
		if 		existing_location.city == '' \
			or 	existing_location.state == '' \
			or 	existing_location.country == '':
			_create_new_location(db, lat_str, long_str, existing_location)
		return existing_location.location_id


def _lookup_location(lat, long_):
	# Using Nominatim as our lookup service for now, because
	# they don't require registration or an API key. The downside
	# is that they have a usage limit of 1 lookup/second.
	# See http://wiki.openstreetmap.org/wiki/Nominatim_usage_policy
	# for more details on the usage policy.
	try:
		geolocator = geocoders.Nominatim()
		# TODO: Hard coding to english location names.
		# We probably want to store these in 'en' and
		# use the message factory translation layer to
		# use client's accept-language headers.
		location = geolocator.reverse((lat, long_), language='en')
		location_address = location.raw.get('address')
		_city = location_address.get('city') or location_address.get( 'town' )
		_state = location_address.get('state')
		_country = location_address.get('country')
	except Exception as e:
		logger.debug('Reverse geolookup for %s, %s failed (%s).', lat, long_, e)
		_city = _state = _country = ''
	return (_city, _state, _country)


def _create_new_location(db, lat_str, long_str, existing_location=None):
	lat = float(lat_str)
	long_ = float(long_str)

	_city, _state, _country = _lookup_location(lat, long_)

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
