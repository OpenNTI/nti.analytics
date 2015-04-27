#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import fudge

from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User

from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..blogs import get_blogs
from ..blogs import _add_blog

class TestBlogs( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_add_blogs(self, mock_find_object):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		results = get_blogs( user )
		assert_that( results, has_length( 0 ))

		blog = PersonalBlogEntry()
		blog._ds_intid = 888
		blog.creator = user
		mock_find_object.is_callable().returns( blog )
		oid = 13

		_add_blog( oid )

		results = get_blogs( user )
		assert_that( results, has_length( 1 ))

