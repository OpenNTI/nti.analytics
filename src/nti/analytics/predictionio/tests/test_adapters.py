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
from hamcrest import contains_string

import unittest

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.analytics.predictionio.interfaces import IOID
from nti.analytics.predictionio.interfaces import IType
from nti.analytics.predictionio.interfaces import IProperties

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.ntiids.ntiids import make_ntiid

from nti.analytics.predictionio.tests import PIOTestCase

import nti.dataserver.tests.mock_dataserver as mock_dataserver

@unittest.SkipTest
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
		
		adapted = IOID(user, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, is_('aizen@nt.com'))

	@WithMockDSTrans
	def test_note_adapter(self):
		user = self.create_user("aizen@nt.com")
							
		note = Note()
		note.title = IPlainTextContentFragment('Release')
		note.tags = (IPlainTextContentFragment('Bankai'),
					 IPlainTextContentFragment('Shikai'))
		note.body = [u'It is not enough to mean well, we actually have to do well']
		note.creator = user.username
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		mock_dataserver.current_transaction.add(note)
		note = user.addContainedObject(note)
		
		prop = IProperties(note, None)
		assert_that(prop, is_not(none()))
		assert_that(prop, has_entry('title', 'Release'))

		adapted = IType(note, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, is_('note'))
		
		adapted = IOID(note, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, contains_string('tag:nextthought.com'))
		
	def test_primitive_adapter(self):
		s = "tag:nextthought.com,2011-10:OU-NTIVideo-LSTD1153_S_2015_History_United_States_1865_to_Present.ntivideo.video_Thesis"
		adapted = IType(s, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, is_('NTIVideo'))
		
		adapted = IOID(s, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, is_(s))
		
		s = "ichigo"
		adapted = IType(s, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, is_(s))
		
		adapted = IOID(s, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, is_(s))
		
		s = 50
		adapted = IOID(s, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, is_(s))
