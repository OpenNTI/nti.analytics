# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.analytics.database import locations as db_locations

from nti.analytics_database.sessions import Location
from nti.analytics.database.sessions import Sessions

from nti.analytics.interfaces import IGeographicalLocation

from nti.analytics.model import GeographicalLocation

logger = __import__('logging').getLogger(__name__)

get_location_list = db_locations.get_location_list
update_missing_locations = db_locations.update_missing_locations


@component.adapter(Location)
@interface.implementer(IGeographicalLocation)
def _from_db_location(db_location):
    kwargs = {}
    for db_attr, attr in (('latitude', 'Latitude'),
                          ('longitude', 'Longitude'),
                          ('city', 'City'),
                          ('state', 'State'),
                          ('country', 'Country'), ):
        kwargs[attr] = getattr(db_location, db_attr, None)
    return GeographicalLocation(**kwargs)

@component.adapter(Sessions)
@interface.implementer(IGeographicalLocation)
def _location_for_session(session):
    location = session.Location
    return IGeographicalLocation(location, None)

