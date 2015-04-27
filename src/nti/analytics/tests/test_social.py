#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import fudge

from datetime import datetime

from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User
from nti.dataserver.users.friends_lists import FriendsList

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..social import get_contacts_added
from ..social import _update_friends_list

class TestSocial( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_add_contact(self, mock_find_object):
		now = datetime.utcnow()
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
		_update_friends_list( oid )
		results = get_contacts_added( user )
		assert_that( results, has_length( 1 ))

		# Remove friend
		fl.removeFriend( user2 )
		_update_friends_list( oid, timestamp=now )
		results = get_contacts_added( user )
		assert_that( results, has_length( 0 ))


