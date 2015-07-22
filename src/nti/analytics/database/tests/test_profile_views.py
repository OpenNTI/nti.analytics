#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

from hamcrest import is_
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_length

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.database import get_analytics_db

from nti.analytics.database.profile_views import EntityProfileViews
from nti.analytics.database.profile_views import EntityProfileActivityViews
from nti.analytics.database.profile_views import EntityProfileMembershipViews
from nti.analytics.database.profile_views import create_profile_view
from nti.analytics.database.profile_views import create_profile_activity_view
from nti.analytics.database.profile_views import create_profile_membership_view

from nti.analytics.database.users import get_user_db_id

from nti.analytics.model import ProfileViewEvent
from nti.analytics.model import ProfileActivityViewEvent
from nti.analytics.model import ProfileMembershipViewEvent

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import User
from nti.dataserver.users import Community

from nti.testing.time import time_monotonically_increases

class TestProfileViews( NTIAnalyticsTestCase ):

	def _test_profile_view(self, event_type, table, create_call):
		# Base
		db = get_analytics_db()
		results = db.session.query( table ).all()
		assert_that( results, has_length( 0 ))

		# Create event
		user = User.create_user( username='new_user1', dataserver=self.ds )
		community = Community.create_community( username='community_name' )
		now = time.time()
		time_length = 30

		event = event_type( user=user.username, ProfileEntity=community.username,
							timestamp=now, Duration=time_length )
		create_call( event, None )

		user_id = get_user_db_id( user )
		target_id = get_user_db_id( community )
		assert_that( user_id, not_none() )
		assert_that( target_id, not_none() )

		results = db.session.query( table ).all()
		assert_that( results, has_length( 1 ))
		record = results[0]
		assert_that( record.user_id, is_( user_id ))
		assert_that( record.target_id, is_( target_id ))
		assert_that( record.timestamp, not_none())
		assert_that( record.time_length, is_( time_length ))

	@WithMockDSTrans
	@time_monotonically_increases
	def test_profile_view(self):
		self._test_profile_view( ProfileViewEvent, EntityProfileViews, create_profile_view )

	@WithMockDSTrans
	@time_monotonically_increases
	def test_profile_activity_view(self):
		self._test_profile_view( ProfileActivityViewEvent, EntityProfileActivityViews,
								create_profile_activity_view )

	@WithMockDSTrans
	@time_monotonically_increases
	def test_profile_membership_view(self):
		self._test_profile_view( ProfileMembershipViewEvent, EntityProfileMembershipViews,
								create_profile_membership_view )
