#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge
from datetime import datetime

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database.users import get_user_db_id

from nti.analytics.database import resource_tags as db_tags

from nti.analytics.database.resource_tags import NoteLikes
from nti.analytics.database.resource_tags import NoteFavorites
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import NotesViewed
from nti.analytics.database.resource_tags import HighlightsCreated
from nti.analytics.database.resource_tags import BookmarksCreated

from nti.dataserver.users.users import Principal

from nti.analytics.database.tests import DEFAULT_INTID

class TestResourceTags(AnalyticsTestBase):

	def setUp(self):
		super( TestResourceTags, self ).setUp()
		self.resource_id = 1
		self.context_path_flat = 'dashboard'
		self.context_path= [ 'dashboard' ]

	@fudge.patch( 	'nti.analytics.database.resource_tags._get_sharing_enum',
					'dm.zope.schema.schema.Object._validate',
					'nti.analytics.database.resource_tags.get_root_context'  )
	def test_note(self, mock_sharing_enum, mock_validate, mock_root_context):
		mock_validate.is_callable().returns( True )
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )
		mock_root_context.is_callable().returns( self.course_id )
		context_path = None

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 0 ) )

		# Pre-emptive delete is ok
		db_tags.delete_note( datetime.now(), DEFAULT_INTID )

		resource_id = 'ntiid:course_resource'
		note_ds_id = DEFAULT_INTID
		note_id = 1
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_ds_id )

		# Create note
		db_tags.create_note( test_user_ds_id, test_session_id, my_note )

		results = db_tags.get_notes( course=self.course_id )
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_id ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( self.resource_id ) )
		# 'UNKNOWN' since we cannot access course and it's scopes.
		assert_that( note.sharing, is_( 'UNKNOWN' ) )
		assert_that( note.deleted, none() )
		assert_that( note.timestamp, not_none() )

		# Note view
		db_tags.create_note_view( 	test_user_ds_id,
									test_session_id, datetime.now(),
									context_path,
									self.course_id, my_note )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesViewed).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_id ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( self.resource_id ) )
		assert_that( note.timestamp, not_none() )

		# Delete note
		db_tags.delete_note( datetime.now(), note_ds_id )

		results = self.session.query(NotesCreated).all()
		assert_that( results, has_length( 1 ) )

		results = db_tags.get_notes( course=self.course_id )
		assert_that( results, has_length( 0 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.deleted, not_none() )

	@fudge.patch( 'nti.analytics.database.resource_tags._get_sharing_enum',
					'nti.analytics.database.resource_tags.get_root_context'  )
	def test_idempotent_note(self, mock_sharing_enum, mock_root_context):
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )
		mock_root_context.is_callable().returns( self.course_id )
		context_path = None

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		note_ds_id = DEFAULT_INTID
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_ds_id )

		# Create note
		db_tags.create_note( test_user_ds_id, test_session_id, my_note )

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_tags.create_note( test_user_ds_id, test_session_id, my_note )

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 1 ) )

		# Note views
		event_time = datetime.now()
		db_tags.create_note_view( 	test_user_ds_id,
									test_session_id, event_time,
									context_path,
									self.course_id, my_note )

		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 1 ) )

		db_tags.create_note_view( 	test_user_ds_id,
									test_session_id, event_time,
									context_path,
									self.course_id, my_note )

		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 1 ) )

	@fudge.patch( 	'nti.analytics.database.resource_tags._get_sharing_enum',
					'dm.zope.schema.schema.Object._validate',
					'nti.analytics.database.resource_tags.get_root_context'   )
	def test_lazy_note_create(self, mock_sharing_enum, mock_validate, mock_root_context):
		mock_validate.is_callable().returns( True )
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )
		mock_root_context.is_callable().returns( self.course_id )
		context_path = None

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		note_ds_id = DEFAULT_INTID
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_ds_id )
		note_creator = Principal( username=str( test_user_ds_id ) )
		note_creator.__dict__['_ds_intid'] = test_user_ds_id
		my_note.creator = note_creator

		# Note view will create our Note record
		db_tags.create_note_view( 	'9999',
									test_session_id, datetime.now(),
									context_path,
									self.course_id, my_note )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 1 ) )

		note_db_id = get_user_db_id( note_creator )

		results = db_tags.get_notes( course=self.course_id )
		assert_that( results, has_length( 1 ) )

		results = self.session.query(NotesCreated).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].user_id, is_( note_db_id ))

	@fudge.patch( 	'nti.analytics.database.resource_tags._get_sharing_enum',
					'dm.zope.schema.schema.Object._validate',
					'nti.analytics.database.resource_tags.get_root_context'    )
	def test_lazy_note_create_parent(self, mock_sharing_enum, mock_validate, mock_root_context):
		mock_validate.is_callable().returns( True )
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )
		mock_root_context.is_callable().returns( self.course_id )

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		note_ds_id = DEFAULT_INTID
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_ds_id )

		# Our parent note
		parent_note = MockNote( resource_id, containerId=resource_id, intid=1111 )
		parent_note_creator = Principal( username=str( test_user_ds_id ) )
		parent_note_creator.__dict__['_ds_intid'] = test_user_ds_id
		parent_note.creator = parent_note_creator
		my_note.__dict__['inReplyTo'] = parent_note

		# Note view will create our Note record
		db_tags.create_note( '9999', test_session_id, my_note )

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 2 ) )

		# Get id
		note_db_id = get_user_db_id( '9999' )
		parent_note_db_id = get_user_db_id( parent_note_creator )

		results = db_tags.get_notes( course=self.course_id )
		assert_that( results, has_length( 2 ) )

		results = self.session.query(NotesCreated).all()
		assert_that( results, has_length( 2 ) )
		result_owners = [x.user_id for x in results]
		assert_that( result_owners, contains_inanyorder( note_db_id, parent_note_db_id ))

	def _do_test_rating(self, table, _rating_call ):
		"For table and rating call, do basic tests."
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

		event_time = datetime.now()
		# Note
		resource_id = 'ntiid:course_resource'
		note_ds_id = DEFAULT_INTID
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_ds_id )

		# Create note
		note_record = db_tags.create_note( test_user_ds_id, test_session_id, my_note )

		delta = 1
		new_user_ds_id = 111111
		_rating_call( my_note, new_user_ds_id,
						test_session_id, event_time, delta )

		results = self.session.query( table ).all()
		assert_that( results, has_length( 1 ) )

		rating_record = results[0]
		assert_that( rating_record.user_id, not_none() )
		assert_that( rating_record.session_id, is_( test_session_id ) )
		assert_that( rating_record.note_id, is_( note_record.note_id ))
		assert_that( rating_record.timestamp, not_none() )
		assert_that( rating_record.creator_id, is_( note_record.user_id ) )
		assert_that( rating_record.course_id, is_( note_record.course_id ))

		# Now revert
		delta = -1
		_rating_call( my_note, new_user_ds_id, test_session_id, event_time, delta )
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

	@fudge.patch( 'nti.analytics.database.resource_tags.get_root_context' )
	def test_likes(self, mock_root_context):
		mock_root_context.is_callable().returns( self.course_id )
		self._do_test_rating( NoteLikes, db_tags.like_note )

	@fudge.patch( 'nti.analytics.database.resource_tags.get_root_context' )
	def test_favorites(self, mock_root_context):
		mock_root_context.is_callable().returns( self.course_id )
		self._do_test_rating( NoteFavorites, db_tags.favorite_note )

	@fudge.patch( 'nti.analytics.database.resource_tags.get_root_context' )
	def test_highlight(self, mock_root_context):
		mock_root_context.is_callable().returns( self.course_id )
		results = self.session.query( HighlightsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Pre-emptive delete is ok
		db_tags.delete_highlight( datetime.now(), DEFAULT_INTID )

		resource_id = 'ntiid:course_resource'
		highlight_ds_id = DEFAULT_INTID
		highlight_id = 1
		my_highlight = MockHighlight( resource_id, intid=highlight_ds_id, containerId=resource_id )

		# Create highlight
		db_tags.create_highlight( test_user_ds_id, test_session_id, my_highlight )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.user_id, is_( 1 ) )
		assert_that( highlight.session_id, is_( test_session_id ) )
		assert_that( highlight.course_id, is_( self.course_id ) )
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.resource_id, is_( self.resource_id ) )
		assert_that( highlight.deleted, none() )
		assert_that( highlight.timestamp, not_none() )

		# Delete highlight
		db_tags.delete_highlight( datetime.now(), highlight_ds_id )

		results = self.session.query(HighlightsCreated).all()
		assert_that( results, has_length( 1 ) )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.deleted, not_none() )
		assert_that( highlight.highlight_ds_id, none() )

	@fudge.patch( 'nti.analytics.database.resource_tags.get_root_context' )
	def test_idempotent_highlights(self, mock_root_context):
		mock_root_context.is_callable().returns( self.course_id )
		results = self.session.query( HighlightsCreated ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		highlight_ds_id = DEFAULT_INTID
		my_highlight = MockHighlight( resource_id, intid=highlight_ds_id, containerId=resource_id )

		# Create highlight
		db_tags.create_highlight( test_user_ds_id, test_session_id, my_highlight )

		results = self.session.query( HighlightsCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_tags.create_highlight( test_user_ds_id, test_session_id, my_highlight )

		results = self.session.query( HighlightsCreated ).all()
		assert_that( results, has_length( 1 ) )

	@fudge.patch( 'nti.analytics.database.resource_tags.get_root_context' )
	def test_bookmark(self, mock_root_context):
		mock_root_context.is_callable().returns( self.course_id )
		results = self.session.query( BookmarksCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Pre-emptive delete is ok
		db_tags.delete_bookmark( datetime.now(), DEFAULT_INTID )

		resource_id = 'ntiid:course_resource'
		bookmark_ds_id = DEFAULT_INTID
		bookmark_id = 1
		my_bookmark = MockHighlight( resource_id, intid=bookmark_ds_id, containerId=resource_id )

		# Create bookmark
		db_tags.create_bookmark( test_user_ds_id, test_session_id, my_bookmark )

		bookmark = self.session.query(BookmarksCreated).one()
		assert_that( bookmark.user_id, is_( 1 ) )
		assert_that( bookmark.session_id, is_( test_session_id ) )
		assert_that( bookmark.course_id, is_( self.course_id ) )
		assert_that( bookmark.bookmark_id, is_( bookmark_id ) )
		assert_that( bookmark.resource_id, is_( self.resource_id ) )
		assert_that( bookmark.deleted, none() )
		assert_that( bookmark.timestamp, not_none() )

		# Delete bookmark
		db_tags.delete_bookmark( datetime.now(), bookmark_ds_id )

		results = self.session.query(BookmarksCreated).all()
		assert_that( results, has_length( 1 ) )

		bookmark = self.session.query(BookmarksCreated).one()
		assert_that( bookmark.bookmark_id, is_( bookmark_id ) )
		assert_that( bookmark.deleted, not_none() )
		assert_that( bookmark.bookmark_ds_id, none() )

	@fudge.patch( 'nti.analytics.database.resource_tags.get_root_context' )
	def test_idempotent_bookmarks(self, mock_root_context):
		mock_root_context.is_callable().returns( self.course_id )
		results = self.session.query( BookmarksCreated ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		bookmark_ds_id = DEFAULT_INTID
		my_bookmark = MockHighlight( resource_id, intid=bookmark_ds_id, containerId=resource_id )

		# Create bookmark
		db_tags.create_bookmark( test_user_ds_id, test_session_id, my_bookmark )

		results = self.session.query( BookmarksCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_tags.create_bookmark( test_user_ds_id, test_session_id, my_bookmark )

		results = self.session.query( BookmarksCreated ).all()
		assert_that( results, has_length( 1 ) )
