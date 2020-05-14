#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime
from datetime import timedelta

from hamcrest import is_
from hamcrest import none
from hamcrest import has_length
from hamcrest import assert_that

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.sessions import _add_session
from nti.analytics.sessions import get_recent_user_sessions
from nti.analytics.sessions import get_user_sessions

from nti.analytics.sessions import _active_session_count

logger = __import__('logging').getLogger(__name__)


class TestSessions( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	def test_adding_sessions(self):
		start = datetime( year=2007, month=3, day=6,
							hour=6, minute=10, second=30 )
		start2 = start + timedelta( seconds=30 )
		duration = 3600
		end = start2 + timedelta( seconds=duration )
		user = User.create_user( username='new_user1', dataserver=self.ds )

		# Empty
		records = get_user_sessions( user )
		assert_that( records, has_length( 0 ) )

		# Test start = end
		_add_session( user.username, '', '', start_time=start, end_time=start )

		records = get_user_sessions( user )
		assert_that( records, has_length( 1 ) )
		assert_that( records[0].SessionStartTime, is_( start ) )
		assert_that( records[0].SessionEndTime, is_( start ) )
		assert_that( records[0].Duration, is_( 0 ) )

		# 30 seconds later, a longer session
		_add_session( user.username, '', '', start_time=start2, end_time=end )

		records = get_user_sessions( user )
		assert_that( records, has_length( 2 ) )

		# Give timestamp boundary (nothing changes)
		records = get_user_sessions( user, timestamp=start )
		assert_that( records, has_length( 2 ) )

		# Split
		records = get_user_sessions( user, timestamp=start + timedelta( seconds=1 ) )
		assert_that( records, has_length( 1 ) )
		assert_that( records[0].SessionStartTime, is_( start2 ) )
		assert_that( records[0].SessionEndTime, is_( end ) )
		assert_that( records[0].Duration, is_( duration ) )

		# Timestamp after the fact
		records = get_user_sessions( user, timestamp=end )
		assert_that( records, has_length( 0 ) )

		# Event with no end time
		_add_session( user.username, '', '', start_time=end, end_time=None )
		records = get_user_sessions( user, timestamp=end )
		assert_that( records, has_length( 1 ) )
		assert_that( records[0].SessionStartTime, is_( end ) )
		assert_that( records[0].SessionEndTime, none() )
		assert_that( records[0].Duration, none() )

	@WithMockDSTrans
	def test_query_sessions(self):
		start = datetime( year=2007, month=3, day=6,
							hour=6, minute=10, second=30 )
		start2 = start + timedelta( seconds=30 )
		duration = 3600
		end = start2 + timedelta( seconds=duration )
		user = User.create_user( username='new_user1', dataserver=self.ds )

		# Empty
		records = get_user_sessions( user )
		assert_that( records, has_length( 0 ) )

		# Test start = end
		_add_session( user.username, '', '', start_time=start, end_time=start )

		# 30 seconds later, a longer session
		_add_session( user.username, '', '', start_time=start2, end_time=end )

		records = get_recent_user_sessions(user, limit=1)
		assert_that( records, has_length( 1 ) )
		assert_that( records[0].SessionStartTime, is_( start2 ) )

		records = get_recent_user_sessions(user, limit=3)
		assert_that( records, has_length( 2 ) )
		assert_that( records[0].SessionStartTime, is_( start2 ) )
		assert_that( records[1].SessionStartTime, is_( start ) )

	@WithMockDSTrans
	def test_active_session_stats(self):
		now = datetime( year=2009, month=3, day=6,
						 hour=6, minute=10, second=30)
		user = User.create_user(username='new_user1')
		user2 = User.create_user(username='new_user2')
		user3 = User.create_user(username='new_user3')

		# Tests are initialized with one session
		baseline = 1

		stats = _active_session_count(_now=now)
		assert_that(stats.count, is_(baseline))

		# add a session that began a long time ago, but never finished
		long_ago = now - timedelta(weeks=52)
		_add_session( user.username, '', '',
		             start_time=long_ago,
		             end_time=None )

		# this should not be active
		stats = _active_session_count(_now=now)
		assert_that(stats.count, is_(baseline))

		# add a session that began long ago, and finished shortly after
		shortly_after_long_ago = long_ago + timedelta(hours=1)
		_add_session( user.username, '', '',
		             start_time=long_ago,
		             end_time=shortly_after_long_ago )

		# this is also not active
		stats = _active_session_count(_now=now)
		assert_that(stats.count, is_(baseline))

		# add a session that began long ago, but just finished (it may be continuing)
		very_recently = now - timedelta(minutes=1)
		_add_session( user.username, '', '',
		             start_time=long_ago,
		             end_time=very_recently )

		# this is active
		baseline += 1
		stats = _active_session_count(_now=now)
		assert_that(stats.count, is_(baseline))

		# add a session that began recently but hasn't finished
		recently = now - timedelta(hours=1)
		_add_session( user.username, '', '',
		             start_time=recently,
		             end_time=None )

		# Same username, same baseline
		stats = _active_session_count(_now=now)
		assert_that(stats.count, is_(baseline))

		# Different username, same data increases baseline
		_add_session(user2.username, '', '',
		             start_time=recently,
		             end_time=None)

		# This is considered active
		baseline += 1
		stats = _active_session_count(_now=now)
		assert_that(stats.count, is_(baseline))

		# add a session (new user) that began recently and just finished
		recently = now - timedelta(hours=1)
		_add_session(user3.username, '', '',
		             start_time=recently,
		             end_time=very_recently )

		# This is considered active
		baseline += 1
		stats = _active_session_count(_now=now)
		assert_that(stats.count, is_(baseline))

		def make_admin(admin_user):
			ds_role_manager = IPrincipalRoleManager(self.ds.dataserver_folder)
			ds_role_manager.assignRoleToPrincipal(ROLE_ADMIN.id, admin_user.username)

		for new_admin_user in (user, user2, user3):
			make_admin(new_admin_user)
			baseline -= 1
			stats = _active_session_count(_now=now)
			assert_that(stats.count, is_(baseline))
