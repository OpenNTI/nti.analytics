#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
from nti.analytics.database.users import get_or_create_user
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from datetime import datetime, timedelta

from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_length

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.database import get_analytics_db

from nti.analytics.database.resource_views import get_video_views_by_user, get_resource_views_by_user,\
	remove_video_data

from nti.analytics_database.resource_views import VideoEvents, ResourceViews

from nti.analytics_database.resources import Resources

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import User

from nti.testing.time import time_monotonically_increases


def video_event(username, timestamp=None, resource_id=None, time_length=None, video_event_type='WATCH'):
	return VideoEvents(user_id=username,
					   session_id=None,
					   timestamp=timestamp,
					   course_id=None,
					   entity_root_context_id=None,
					   context_path=None,
					   resource_id=resource_id,
					   time_length=time_length,
					   video_event_type=video_event_type,
					   video_start_time=0,
					   video_end_time=None,
					   with_transcript=False,
					   play_speed=None,
					   player_configuration=None)


def resource_event(username, timestamp=None, resource_id=None, time_length=None):
	return ResourceViews(user_id=username, resource_id=resource_id, timestamp=timestamp, time_length=time_length)


class TestResourceViews(NTIAnalyticsTestCase):

	@WithMockDSTrans
	@time_monotonically_increases
	def test_video_view(self):
		table = VideoEvents

		# Base
		db = get_analytics_db()
		results = db.session.query(table).all()
		assert_that(results, has_length(0))

		# Create event
		user = User.create_user(username='new_user1', dataserver=self.ds)
		user2 = User.create_user(username='new_user2', dataserver=self.ds)

		user_record1 = get_or_create_user(user)
		user_record2 = get_or_create_user(user2)
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
			video_event(user_record1.user_id,
						timestamp=now,
						resource_id=resource.resource_id,
						time_length=5,
						video_event_type='WATCH'),
			video_event(user_record1.user_id,
						timestamp=now,
						resource_id=resource.resource_id,
						time_length=5,
						video_event_type='WATCH'),
			video_event(user_record2.user_id,
						timestamp=now,
						resource_id=resource.resource_id,
						time_length=5,
						video_event_type='WATCH'),

			# Excluded b/c time_length==0
			video_event(user_record1.user_id,
						timestamp=now,
						resource_id=resource.resource_id,
						time_length=0,
						video_event_type='WATCH'),

			# Excluded b/c video_event_type != 'WATCH'
			video_event(user_record1.user_id,
						timestamp=now,
						resource_id=resource.resource_id,
						time_length=0,
						video_event_type='SKIP'),

			# Excluded b/c timestamp is prior to `now`
			video_event(user_record1.user_id,
						timestamp=before_window,
						resource_id=resource.resource_id,
						time_length=0,
						video_event_type='SKIP'),
		]

		for event in events:
			db.session.add(event)

		db.session.flush()

		results = db.session.query(table).all()
		assert_that(results, has_length(6))

		user_map = {user_id: count for user_id, count in get_video_views_by_user(timestamp=now, max_timestamp=max_time)}

		assert_that(user_map, has_length(2))
		assert_that(user_map, has_entry(user_record1.user_id, 2))
		assert_that(user_map, has_entry(user_record2.user_id, 1))

		db.session.commit()
		remove_video_data(user, resource.resource_ds_id)
		db.session.flush()
		user_map = {user_id: count for user_id, count in get_video_views_by_user(timestamp=now, max_timestamp=max_time)}

		assert_that(user_map, has_length(1))
		assert_that(user_map, has_entry(user_record2.user_id, 1))


	@WithMockDSTrans
	@time_monotonically_increases
	def test_resource_view(self):
		table = ResourceViews

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
			resource_event(user.username,
						   timestamp=now,
						   resource_id=resource.resource_id,
						   time_length=5),
			resource_event(user.username,
						   timestamp=now,
						   resource_id=resource.resource_id,
						   time_length=5),
			resource_event(user2.username,
						   timestamp=now,
						   resource_id=resource.resource_id,
						   time_length=5),

			# Excluded b/c timestamp is prior to `now`
			resource_event(user2.username,
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
					get_resource_views_by_user(timestamp=now, max_timestamp=max_time)}

		assert_that(user_map, has_length(2))
		assert_that(user_map, has_entry('new_user1', 2))
		assert_that(user_map, has_entry('new_user2', 1))


