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

from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..sessions import _add_session
from ..sessions import get_user_sessions

class TestSessions( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	def test(self):
		start = datetime( year=2007, month=3, day=6,
							hour=6, minute=10, second=30 )
		seconds_delta = 3600
		end = start + timedelta( seconds=seconds_delta )
		user = User.create_user( username='new_user1', dataserver=self.ds )

		# Empty
		records = get_user_sessions( user )
		assert_that( records, has_length( 0 ) )

		# Test start = end
		_add_session( user.username, '', '', start_time=start, end_time=start )

		records = get_user_sessions( user )
		assert_that( records, has_length( 1 ) )

		# One hour gap
		_add_session( user.username, '', '', start_time=start, end_time=end )

		records = get_user_sessions( user )
		assert_that( records, has_length( 2 ) )

		# Give timestamp boundary (nothing changes)
		records = get_user_sessions( user, timestamp=start )
		assert_that( records, has_length( 2 ) )

		# Timestamp after the fact
		records = get_user_sessions( user, timestamp=end )
		assert_that( records, has_length( 0 ) )

