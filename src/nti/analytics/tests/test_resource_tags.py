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

from nti.contenttypes.courses.courses import CourseInstance
from nti.dataserver.contenttypes.highlight import Highlight
from nti.dataserver.contenttypes.note import Note
from nti.dataserver.contenttypes.bookmark import Bookmark

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..resource_tags import get_notes
from ..resource_tags import get_bookmarks
from ..resource_tags import get_highlights
from ..resource_tags import _add_note
from ..resource_tags import _add_bookmark
from ..resource_tags import _add_highlight

class TestResourceTags( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid',
				'nti.analytics.resolvers.get_container_context',
				'nti.analytics.database.resource_tags._get_sharing_enum' )
	def test_add_notes(self, mock_find_object, mock_container_context, mock_sharing_enum):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		results = get_notes( user )
		assert_that( results, has_length( 0 ))

		note = Note()
		note._ds_intid = 888
		note.body = ('test222',)
		note.creator = user
		note.containerId = 'tag:nti:foo'
		user.addContainedObject( note )
		course = CourseInstance()
		mock_find_object.is_callable().returns( note )
		mock_container_context.is_callable().returns( course )
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )
		oid = 13

		_add_note( oid )

		results = get_notes( user )
		assert_that( results, has_length( 1 ))

		results = get_notes( user, top_level_only=True )
		assert_that( results, has_length( 1 ))

		results = get_notes( user, replies_only=True )
		assert_that( results, has_length( 0 ))

		# Reply-to
		note2 = Note()
		note2.body = ('test',)
		note2.creator = user
		note2.inReplyTo = note
		note2._ds_intid = 777
		mock_find_object.is_callable().returns( note2 )

		_add_note( oid+1 )

		results = get_notes( user )
		assert_that( results, has_length( 2 ))

		results = get_notes( user, top_level_only=True )
		assert_that( results, has_length( 1 ))

		results = get_notes( user, replies_only=True )
		assert_that( results, has_length( 1 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid',
				'nti.analytics.resolvers.get_container_context')
	def test_add_highlight(self, mock_find_object, mock_container_context):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		results = get_highlights( user )
		assert_that( results, has_length( 0 ))

		highlight = Highlight()
		highlight.creator = user
		course = CourseInstance()
		mock_find_object.is_callable().returns( highlight )
		mock_container_context.is_callable().returns( course )
		oid = 13

		_add_highlight( oid )

		results = get_highlights( user )
		assert_that( results, has_length( 1 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid',
				'nti.analytics.resolvers.get_container_context')
	def test_add_bookmark(self, mock_find_object, mock_container_context):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		results = get_bookmarks( user )
		assert_that( results, has_length( 0 ))

		bookmark = Bookmark()
		bookmark.creator = user
		course = CourseInstance()
		mock_find_object.is_callable().returns( bookmark )
		mock_container_context.is_callable().returns( course )
		oid = 13

		_add_bookmark( oid )

		results = get_bookmarks( user )
		assert_that( results, has_length( 1 ))

