#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import all_of
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

import fudge

from zope import component

from nti.analytics.database import sessions
from nti.analytics.database import locations
from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.root_context import get_root_context_id

from nti.contenttypes.courses import courses
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager

from nti.dataserver.users.users import User
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.analytics.database.tests import NTIAnalyticsTestCase

course = 'tag:nextthought.com,2011-10:OU-HTML-CLC3403_LawAndJustice.course_info'

class TestLocations(NTIAnalyticsTestCase):

	def setUp(self):
		self.db = AnalyticsDB(dburi='sqlite://', testmode=True)
		component.getGlobalSiteManager().registerUtility(self.db, IAnalyticsDB)
		self.session = self.db.session

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility(self.db)
		self.session.close()

	def _create_course(self):
		content_unit = find_object_with_ntiid(course)
		course_obj = self.course = ICourseInstance(content_unit)
		get_root_context_id(self.db, course_obj, create=True)

	@WithMockDSTrans
	@fudge.patch('nti.analytics.database.sessions._lookup_coordinates_for_ip')
	@fudge.patch('nti.analytics.database.sessions._lookup_location')
	def test_location_list(self, fake_ip_lookup, fake_location_lookup):
		# Create a fake user and course
		principal = User.create_user(username='sjohnson@nextthought.com', dataserver=self.ds)
		self.ds.root[principal.id] = principal
		admin = courses.CourseAdministrativeLevel()
		self.ds.root['admin'] = admin
		course = courses.CourseInstance()
		admin['course'] = course
		self.section = course.SubInstances['section1'] = courses.ContentCourseSubInstance()
		self.principal = principal
		self.course = course
		manager = ICourseEnrollmentManager(course)

		# Enroll the user in the course
		manager.enroll(principal, scope='Public')

		# Use fake web services to look up IP coordinates and location data
		# Assign this user an IP address and therefore a location.
		# This user lives at Google.
		fake_location_lookup.is_callable().calls(fake_location_data_for_coordinates)
		fake_ip_lookup.is_callable().calls(fake_locations_for_ips)
		sessions._create_ip_location(self.db, '8.8.8.8', 1)

		location_results = locations.get_location_list(course, 'ALL_USERS')

		# Verify that we got the correct user data
		assert_that(location_results, has_length(1))
		assert_that(location_results, has_item(all_of(has_entry('number_of_students', 1),
													  has_entry('city', 'The Googleplex'),
													  has_entry('latitude', 37.422),
													  has_entry('longitude', 122.084))))

		# Create another user, and enroll them in the "ForCredit" scope
		second_user = User.create_user(username='zachary.roux@nextthought.com', dataserver=self.ds)
		self.ds.root[second_user.id] = second_user
		self.second_user = second_user
		manager.enroll(second_user, scope='ForCredit')
		sessions._create_ip_location(self.db, '1.2.3.4', 2)

		# We should see both users in ALL_USERS, but only the second user in ForCredit.

		# Check the ALL_USERS scope
		location_results = locations.get_location_list(course, 'ALL_USERS')
		assert_that(location_results, has_length(2))
		assert_that(location_results, has_item(all_of(has_entry('number_of_students', 1),
													  has_entry('city', 'The Googleplex'),
													  has_entry('latitude', 37.422),
													  has_entry('longitude', 122.084))))

		assert_that(location_results, has_item(all_of(has_entry('number_of_students', 1),
													  has_entry('city', 'Norman'),
													  has_entry('latitude', 12.345),
													  has_entry('longitude', 67.890))))

		# Check the ForCredit scope
		location_results = locations.get_location_list(course, 'ForCredit')
		assert_that(location_results, has_length(1))
		assert_that(location_results, has_item(all_of(has_entry('number_of_students', 1),
													  has_entry('city', 'Norman'),
													  has_entry('latitude', 12.345),
													  has_entry('longitude', 67.890))))

def fake_locations_for_ips(ip_address):
	# Helper method for fudging the IP lookup service
	fake_results = fudge.Fake()
	if ip_address == "8.8.8.8":
		return fake_results.has_attr(location=[37.422, 122.084], country="US")
	elif ip_address == "1.2.3.4":
		return fake_results.has_attr(location=[12.345, 67.890], country="US")

def fake_location_data_for_coordinates(latitude, longitude):
	# Helper method for fudging the reverse geo-lookup service
	if latitude == 37.422 and longitude == 122.084:
		return ("The Googleplex", "California", "USA")

	if latitude == 12.345 and longitude == 67.890:  # fake coordinates :P
		return ("Norman", "Oklahoma", "USA")
