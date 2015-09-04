#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Returns a list representation of the geographical 
locations of users within a course.
"""

from nti.analytics.database import get_analytics_db
from nti.analytics.database.sessions import IpGeoLocation, Location
from nti.app.products.courseware_reports.views import ALL_USERS
from nti.dataserver.interfaces import IEnumerableEntityContainer
from nti.dataserver.users.users import User

def _get_location_ids_for_users( db, user_ids ): 
    location_ids = []
    for user_id in user_ids:
        ips_for_user = db.session.query( IpGeoLocation ).filter( IpGeoLocation.user_id == user_id).all()
        for row in ips_for_user:
            location_ids.append( row.location_id )
    return location_ids

def _get_locations_for_ids( db, location_ids, location_counts ):
    location_rows = []
    for location_id in location_ids:
        location = db.session.query( Location ).filter( Location.location_id == location_id ).first()
        # count the number of times this location is being used
        if location_id in location_counts:
            location_counts[location_id] += 1
        else: 
            # return a list of distinct locations,
            # so only add each location once
            location_rows.append(location)
            location_counts[location_id] = 1
    return location_rows

def _get_location_data( locations, location_counts ):

    def get_user_label( number_of_users ):
        if number_of_users > 1:
            return '%s users' % number_of_users
        else:
            return '1 user'
    
    db_data = []
    
    for location in locations:

        city = location.city
        state = location.state
        country = location.country

        if country == 'United States of America':
            if city and state:
                label =  "%s, %s" % ( city, state )
            elif state:
                label =  "%s" % state
            else:
                label = ''
        else:
            if city and country:
                label =  "%s, %s" % ( city, country )
            elif country:
                label =  "%s" % country
            else:
                label = ''

        label = '%s (%s)' % (label, get_user_label(location_counts[location.location_id]))

        number_of_users_in_location = location_counts[location.location_id]

        locationData = {
                    'latitude': float( location.latitude ), 
                    'longitude': float( location.longitude ), 
                    'label': label, 
                    'city': city,
                    'state': state,
                    'country': country,
                    'number_of_students': number_of_users_in_location}
        # append the data for this location as a location element in db_data
        db_data.append( locationData )
        
    return db_data

def get_location_list(course, enrollment_scope):

    db = get_analytics_db()
    location_counts = {}
    
    user_ids = _get_enrolled_user_ids( course, enrollment_scope )
    location_ids = _get_location_ids_for_users(db, user_ids)
    locations = _get_locations_for_ids( db, location_ids, location_counts )
    data = _get_location_data( locations, location_counts )
    
    return data
    
def _get_enrolled_user_ids(course, enrollment_scope):
    """
    Gets a list of the user ids for the specified course and enrollment scope.
    """
    users = _get_enrollment_scope_list(course)
    user_ids = []
    for user in users[enrollment_scope]:
        user_ids.append(user.user_id)
    return user_ids

    # TODO: Since this is nearly the same code as in the
    # __init__.py of coursewarereports/views, maybe we should
    # make a more generic method and use it both places?
def _get_enrollment_scope_list( course, instructors=set() ):
    "Build a dict of scope_name to user objects."
    results = {}
    # Lumping purchased in with public.
    public_scope = course.SharingScopes.get( 'Public', None )
    purchased_scope = course.SharingScopes.get( 'Purchased', None )
    non_public_users = set()
    for scope_name in course.SharingScopes:
        scope = course.SharingScopes.get( scope_name, None )
    
        if         scope is not None \
            and scope not in (public_scope, purchased_scope):
            # If our scope is not 'public'-ish, store it separately.
            # All credit-type users should end up in ForCredit.
            scope_users = {x.lower() for x in IEnumerableEntityContainer(scope).iter_usernames()}
            scope_users = scope_users - instructors
            users = []
            for username in scope_users:
                user = User.get_user(username)
                if user is not None:
                    users.append(user)
            results[scope_name] = users
            non_public_users = non_public_users.union( users )
    
    all_usernames = {x.lower() for x in IEnumerableEntityContainer(public_scope).iter_usernames()}
    all_users = []
    for username in all_usernames:
        user = User.get_user(username)
        if user is not None:
            users.append(user)
    public_usernames = all_usernames - non_public_users - instructors
    public_users = [] 
    for username in public_usernames:
        user = User.get_user(username)
        if user is not None:
            public_users.append(user)
    results['Public'] = public_users
    results[ALL_USERS] = all_users
    return results
