#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.analytics.predictionio.interfaces import ITypes
from nti.analytics.predictionio.interfaces import IProperties

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.predictionio.tests import PIOTestCase

class TestAdapters(PIOTestCase):

	def create_user(self, username='nt@nti.com', password='temp001', **kwargs):
		usr = User.create_user(self.ds, username=username, password=password, **kwargs)
		return usr

	@WithMockDSTrans
	def test_entity_adapter(self):
		user = self.create_user("aizen@nt.com",
								external_value={u'alias':u"traitor",
												u'realname':'aizen'})

		adapted = IProperties(user, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, has_length(2))
		assert_that(adapted, has_entry('name', 'aizen'))
		assert_that(adapted, has_entry('alias', 'traitor'))

	@WithMockDSTrans
	def test_note_adapter(self):
		note = Note()
		note.title = IPlainTextContentFragment('Release')
		note.tags = (IPlainTextContentFragment('Bankai'),
					 IPlainTextContentFragment('Shikai'))
		prop = IProperties(note, None)
		assert_that(prop, is_not(none()))
		assert_that(prop, has_entry('title', 'Release'))
		types = ITypes(note, None)
		assert_that(types, is_not(none()))
		assert_that(types, is_(('note', 'bankai', 'shikai')))

