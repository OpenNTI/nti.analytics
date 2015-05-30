#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import fudge

from calendar import timegm as _calendar_timegm

from datetime import datetime

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User
from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..social import _add_dfl
from ..social import _add_dfl_member
from ..social import get_contacts_added
from ..social import _update_friends_list
from ..social import get_groups_created
from ..social import get_groups_joined

class TestSocial( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_add_contact(self, mock_find_object):
		# We lose some precision
		now = datetime.utcnow()
		now = now.replace( microsecond=0 )

		username1 = 'new_user1'
		user = User.create_user( username=username1, dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )
		results = get_contacts_added( user )
		assert_that( results, has_length( 0 ))

		fl = FriendsList( username=username1 )
		fl.creator = user
		fl.__name__ = 'mycontacts'
		fl.addFriend( user2 )
		mock_find_object.is_callable().returns( fl )
		oid = 13

		# Add friend
		_update_friends_list( oid, timestamp=now )
		results = get_contacts_added( user )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Contact, is_( user2 ) )
		assert_that( results[0].user, is_( user ) )
		assert_that( results[0].timestamp, is_( now ) )

		# Remove friend
		fl.removeFriend( user2 )
		_update_friends_list( oid, timestamp=now )
		results = get_contacts_added( user )
		assert_that( results, has_length( 0 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_groups(self, mock_find_object):
		# We lose some precision
		now = datetime.utcnow()
		now = now.replace( microsecond=0 )

		username1 = 'new_user1'
		user = User.create_user( username=username1, dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )
		fl = DynamicFriendsList( username=username1 )
		fl.creator = user
		fl.createdTime = _calendar_timegm( now.timetuple() )
		fl._ds_intid = 123456
		oid = 13

		# Base
		results = get_groups_created( user )
		assert_that( results, has_length( 0 ))
		results = get_groups_joined( user2 )
		assert_that( results, has_length( 0 ))

		# Add dfl
		mock_find_object.is_callable().returns( fl )
		_add_dfl( oid )

		results = get_groups_created( user )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Group, is_( fl ) )
		assert_that( results[0].user, is_( user ) )
		assert_that( results[0].timestamp, is_( now ) )

		results = get_groups_joined( user2 )
		assert_that( results, has_length( 0 ))

		# Add friend
		_add_dfl_member( user2, fl, timestamp=now )
		results = get_groups_created( user )
		assert_that( results, has_length( 1 ))

		results = get_groups_joined( user2 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Group, is_( fl ) )
		assert_that( results[0].user, is_( user ) )
		assert_that( results[0].timestamp, is_( now ) )

		# Not only the founder, but also (not?) a member
		results = get_groups_joined( user )
		assert_that( results, has_length( 0 ))

