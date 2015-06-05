#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import fudge

from hamcrest import is_
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
from ..resource_tags import _like_note
from ..resource_tags import _favorite_note
from ..resource_tags import _add_bookmark
from ..resource_tags import _add_highlight
from ..resource_tags import get_replies_to_user
from ..resource_tags import get_user_replies_to_others
from ..resource_tags import get_likes_for_users_notes
from ..resource_tags import get_favorites_for_users_notes

class TestNotes( NTIAnalyticsTestCase ):

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
		course._ds_intid = 123456
		mock_find_object.is_callable().returns( note )
		mock_container_context.is_callable().returns( course )
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )
		oid = 13

		_add_note( oid )

		# Fetch
		results = get_notes( user )
		assert_that( results, has_length( 1 ))
		note_record = results[0]
		assert_that( note_record.Note, is_( note ) )
		assert_that( note_record.IsReply, is_( False ) )
		assert_that( note_record.RootContext, is_( course ) )
		assert_that( note_record.NoteLength, is_( 7 ))
		assert_that( note_record.user, is_( user ) )

		results = get_notes( user )
		assert_that( results, has_length( 1 ))

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

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid',
				'nti.analytics.resolvers.get_container_context',
				'nti.analytics.database.resource_tags._get_sharing_enum' )
	def test_reply_comments(self, mock_find_object, mock_container_context, mock_sharing_enum):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		course = CourseInstance()
		mock_container_context.is_callable().returns( course )
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )

		# Create note
		note1 = Note()
		note1.body = ('test222',)
		note1.creator = user1
		note1.containerId = 'tag:nti:foo'
		user1.addContainedObject( note1 )
		mock_find_object.is_callable().returns( note1 )
		_add_note( note1 )

		results = get_replies_to_user( user1 )
		assert_that( results, has_length( 0 ))
		results = get_user_replies_to_others( user2 )
		assert_that( results, has_length( 0 ))

		# Reply-to
		note2 = Note()
		note2.creator = user2
		note2.body = ('test222',)
		note2.__parent__ = note1
		note2.containerId = 'tag:nti:foo'
		user2.addContainedObject( note2 )
		note2.inReplyTo = note1
		mock_find_object.is_callable().returns( note2 )
		_add_note( note2 )

		# Both should return same record
		# Replies to user; User replies to others
		results = get_replies_to_user( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Note, is_( note2 ))
		assert_that( results[0].user, is_( user2 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].RepliedToUser, is_( user1 ))

		results = get_user_replies_to_others( user2 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Note, is_( note2 ))
		assert_that( results[0].user, is_( user2 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].RepliedToUser, is_( user1 ))

		# The reverse is nothing
		results = get_replies_to_user( user2 )
		assert_that( results, has_length( 0 ))
		results = get_user_replies_to_others( user1 )
		assert_that( results, has_length( 0 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid',
				'nti.analytics.resolvers.get_container_context',
				'nti.analytics.database.resource_tags._get_sharing_enum' )
	def test_rated_notes(self, mock_find_object, mock_container_context, mock_sharing_enum):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		course = CourseInstance()
		mock_container_context.is_callable().returns( course )
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )

		# Create note
		note1 = Note()
		note1.body = ('test222',)
		note1.creator = user1
		note1.containerId = 'tag:nti:foo'
		user1.addContainedObject( note1 )
		mock_find_object.is_callable().returns( note1 )
		_add_note( note1 )

		# Base
		results = get_likes_for_users_notes( user1 )
		assert_that( results, has_length( 0 ))

		results = get_favorites_for_users_notes( user1 )
		assert_that( results, has_length( 0 ))

		# Like note
		mock_find_object.is_callable().returns( note1 )
		_like_note( 11, delta=1, username=user2.username )

		results = get_likes_for_users_notes( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].ObjectCreator, is_( user1 ))
		assert_that( results[0].user, is_( user2 ))

		results = get_favorites_for_users_notes( user1 )
		assert_that( results, has_length( 0 ))

		# Favorite note
		mock_find_object.is_callable().returns( note1 )
		_favorite_note( 11, delta=1, username=user2.username )

		results = get_likes_for_users_notes( user1 )
		assert_that( results, has_length( 1 ))

		results = get_favorites_for_users_notes( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].ObjectCreator, is_( user1 ))
		assert_that( results[0].user, is_( user2 ))


class TestHighlights( NTIAnalyticsTestCase ):

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
		highlight_record = results[0]
		assert_that( highlight_record.Highlight, is_( highlight ) )
		assert_that( highlight_record.user, is_( user ) )
		assert_that( highlight_record.RootContext, is_( course ) )


class TestBookmarks( NTIAnalyticsTestCase ):

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
		bookmark_record = results[0]
		assert_that( bookmark_record.Bookmark, is_( bookmark ) )
		assert_that( bookmark_record.user, is_( user ) )
		assert_that( bookmark_record.RootContext, is_( course ) )


