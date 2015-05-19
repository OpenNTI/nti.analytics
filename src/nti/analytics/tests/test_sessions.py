#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime
from datetime import timedelta

from hamcrest import is_
from hamcrest import none
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..sessions import _add_session
from ..sessions import get_user_sessions

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
