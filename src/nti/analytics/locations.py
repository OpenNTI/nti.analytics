# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.analytics_database.sessions import Location

from nti.analytics.database import locations as db_locations

from nti.analytics.interfaces import IAnalyticsSession
from nti.analytics.interfaces import IGeographicalLocation

from nti.analytics.model import GeographicalLocation

update_missing_locations = db_locations.update_missing_locations
get_location_list = db_locations.get_location_list
location_for_ip = db_locations.location_for_ip

@component.adapter( Location )
@interface.implementer( IGeographicalLocation )
def _from_db_location(db_location):
    kwargs = {}
    for db_attr, attr in (('latitude', 'Latitude'),
                          ('longitude', 'Longitude'),
                          ('city', 'City'),
                          ('state', 'State'),
                          ('country', 'Country'), ):
        kwargs[attr] = getattr(db_location, db_attr, None)
    return GeographicalLocation(**kwargs)

@component.adapter( IAnalyticsSession )
@interface.implementer( IGeographicalLocation )
def _location_for_session(session):
    location = location_for_ip(session.ip_addr)
    return IGeographicalLocation(location) if location else None

