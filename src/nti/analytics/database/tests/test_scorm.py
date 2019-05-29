#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from datetime import datetime, timedelta

from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_length

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.database import get_analytics_db

from nti.analytics.database.scorm import get_launch_records_by_user

from nti.analytics_database.resources import Resources

from nti.analytics_database.scorm import SCORMPackageLaunches

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import User

from nti.testing.time import time_monotonically_increases


def launch_record(username, timestamp=None, resource_id=None, time_length=None):
	return SCORMPackageLaunches(user_id=username, resource_id=resource_id, timestamp=timestamp, time_length=time_length)


class TestLaunchRecordsByUser(NTIAnalyticsTestCase):

	@WithMockDSTrans
	@time_monotonically_increases
	def test_launch_records(self):
		table = SCORMPackageLaunches

		# Base
		db = get_analytics_db()
		results = db.session.query(table).all()
		assert_that(results, has_length(0))

		# Create event
		user = User.create_user(username='new_user1', dataserver=self.ds)
		user2 = User.create_user(username='new_user2', dataserver=self.ds)

		now = datetime.now()
		time_length = 30
		before_window = now - timedelta(seconds=time_length)
		max_time = now + timedelta(seconds=time_length)

		resource = Resources(resource_ds_id='tag:nextthought.com,2018-09:specific',
							 max_time_length=500)

		db.session.add(resource)
		db.session.flush()

		events = [
			# Events included in user activity
			launch_record(user.username,
						  timestamp=now,
						  resource_id=resource.resource_id,
						  time_length=5),
			launch_record(user.username,
						  timestamp=now,
						  resource_id=resource.resource_id,
						  time_length=5),
			launch_record(user2.username,
						  timestamp=now,
						  resource_id=resource.resource_id,
						  time_length=5),

			# Excluded b/c timestamp is prior to `now`
			launch_record(user2.username,
						  timestamp=before_window,
						  resource_id=resource.resource_id,
						  time_length=5)
		]

		for event in events:
			db.session.add(event)

		db.session.flush()

		results = db.session.query(table).all()
		assert_that(results, has_length(4))

		user_map = {user_id: count for user_id, count in
					get_launch_records_by_user(timestamp=now, max_timestamp=max_time)}

		assert_that(user_map, has_length(2))
		assert_that(user_map, has_entry('new_user1', 2))
		assert_that(user_map, has_entry('new_user2', 1))
