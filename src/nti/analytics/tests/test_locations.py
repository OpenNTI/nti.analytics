#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_properties

from nti.analytics_database.sessions import Location

from nti.analytics.common import timestamp_type

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



