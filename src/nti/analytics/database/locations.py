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

from nti.dataserver.users.users import User
from nti.dataserver.interfaces import IEnumerableEntityContainer

from .users import get_user_db_id

from .sessions import IpGeoLocation, Location

from . import get_analytics_db

ALL_USERS = 'ALL_USERS'

def _get_location_ids_for_users(db, user_ids):
	location_ids = []
	for user_id in user_ids:
		ips_for_user = db.session.query(IpGeoLocation).filter(IpGeoLocation.user_id == user_id).all()
		for row in ips_for_user:
			location_ids.append(row.location_id)
	return location_ids

def _get_locations_for_ids(db, location_ids, location_counts):
	location_rows = []
	for location_id in location_ids:
		location = db.session.query(Location).filter(Location.location_id == location_id).first()
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
		label = u'%s (%s)' % (label, get_user_label(location_counts[location.location_id]))

		number_of_users_in_location = location_counts[location.location_id]
		
		locationData = {
				'latitude': float(location.latitude),
				'longitude': float(location.longitude),
				'label': label,
				'city': city,
				'state': state,
				'country': country,
				'number_of_students': number_of_users_in_location}
		# append the data for this location as a location element in db_data
		db_data.append(locationData)

	return db_data

def get_location_list(course, enrollment_scope):

	db = get_analytics_db()
	location_counts = {}

	user_ids = _get_enrolled_user_ids(course, enrollment_scope)
	location_ids = _get_location_ids_for_users(db, user_ids)
	locations = _get_locations_for_ids(db, location_ids, location_counts)
	data = _get_location_data(locations, location_counts)

	return data

def _get_enrolled_user_ids(course, enrollment_scope):
	"""
	Gets a list of the user ids for the specified course and enrollment scope.
	"""
	users = _get_enrollment_scope_dict(course, set(course.instructors))
	user_ids = []
	usernames_for_scope = users[enrollment_scope]
	for username in usernames_for_scope:
		user = User.get_user(username)
		id_ = get_user_db_id(user)
		if id_ is not None:
			user_ids.append(id_)
	return user_ids

	# Note: this is the same code as in the
	# _get_enrollment_scope_dic method in
	# coursewarereports/views/__init__.py.

def _get_enrollment_scope_dict(course=ALL_USERS, instructors=set()):
	
	"""
	Build a dict of scope_name to usernames.
	"""
	# XXX We are not exposing these multiple scopes in many places,
	# including many reports and in TopCreators.
	# XXX This is confusing if we are nesting scopes.  Perhaps
	# it makes more sense to keep things in the Credit/NonCredit camps.
	# Seems like it would make sense to have an Everyone scope...
	# { Everyone: { Public : ( Open, Purchased ), ForCredit : ( FCD, FCND ) }}
	results = {}
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
