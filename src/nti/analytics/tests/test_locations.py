#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_properties

from nti.analytics_database.sessions import Location

from nti.analytics.interfaces import IGeographicalLocation

from nti.analytics.tests import NTIAnalyticsTestCase

class TestLocation( NTIAnalyticsTestCase ):
	"""
	Tests geo location related information.
	"""

	def test_db_location_to_geolocation(self):
		location = Location()
		location.latitude = 'foo'
		location.longitude = 'bar'
		location.city = 'baz'
		location.state = 'ok'
		location.country = 'usa'

		geo_loc = IGeographicalLocation(location)

		assert_that(geo_loc, has_properties('Latitude', 'foo',
		                                    'Longitude', 'bar',
		                                    'City', 'baz',
		                                    'State', 'ok',
		                                    'Country', 'usa'))



