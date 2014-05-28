#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.users import User
from nti.dataserver.users import Community
from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry
from nti.dataserver.contenttypes.forums.post import PersonalBlogComment
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.graphdb import relationships
from nti.graphdb import interfaces as graph_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.graphdb.tests import ConfiguringTestBase

from hamcrest import (assert_that, has_length, has_entry, has_property,
					  is_, is_in, none, is_not)

class TestAdapters(ConfiguringTestBase):

	def _create_user(self, username='nt@nti.com', password='temp001', **kwargs):
		usr = User.create_user(self.ds, username=username, password=password, **kwargs)
		return usr

	@WithMockDSTrans
	def test_entity_adapter(self):
		user = self._create_user(
						"owner@bar",
						 external_value={u'alias':u"owner", u'realname':'na marsh'})

		labels = graph_interfaces.ILabelAdapter(user, None)
		assert_that(labels, is_not(none()))
		assert_that(labels, has_length(1))
		assert_that('user', is_in(labels))

		props = graph_interfaces.IPropertyAdapter(user, None)
		assert_that(props, is_not(none()))
		assert_that(props, has_length(6))
		assert_that(props, has_entry('username', 'owner@bar'))
		assert_that(props, has_entry('alias', 'owner'))
		assert_that(props, has_entry('name', 'na marsh'))
		assert_that(props, has_entry('type', 'User'))

	@WithMockDSTrans
	def test_community_adapter(self):
		comm = Community.create_community(
							username='cs',
							external_value={u'alias':u"ComSci", u'realname':'OUCS'})

		labels = graph_interfaces.ILabelAdapter(comm, None)
		assert_that(labels, is_not(none()))
		assert_that(labels, has_length(1))
		assert_that('community', is_in(labels))

		props = graph_interfaces.IPropertyAdapter(comm, None)
		assert_that(props, is_not(none()))
		assert_that(props, has_length(6))
		assert_that(props, has_entry('username', 'cs'))
		assert_that(props, has_entry('alias', 'ComSci'))
		assert_that(props, has_entry('name', 'OUCS'))
		assert_that(props, has_entry('type', 'Community'))

	@WithMockDSTrans
	def test_generic_adapter(self):
		obj = object()
		labels = graph_interfaces.ILabelAdapter(obj, None)
		assert_that(labels, is_not(none()))
		assert_that(labels, has_length(0))

		props = graph_interfaces.IPropertyAdapter(obj, None)
		assert_that(props, is_not(none()))
		assert_that(props, has_length(1))
		assert_that(props, has_entry('created', is_not(none())))

	@WithMockDSTrans
	def test_unique_entity_attr_adapter(self):
		user = self._create_user(
						"owner@bar",
						external_value={u'alias':u"owner", u'realname':'na marsh'})
		adapted = graph_interfaces.IUniqueAttributeAdapter(user, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, has_property('key', 'username'))
		assert_that(adapted, has_property('value', 'owner@bar'))
		
		obj = object()
		adapted = graph_interfaces.IUniqueAttributeAdapter(obj, None)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, has_property('key', is_(none())))
		assert_that(adapted, has_property('value', is_(none())))

	@WithMockDSTrans
	def test_unique_friendship_attr_adapter(self):
		user1 = self._create_user("user1@bar")
		user2 = self._create_user("user2@bar")
		adapted = component.queryMultiAdapter((user1, user2, relationships.FriendOf()),  
											  graph_interfaces.IUniqueAttributeAdapter)
		assert_that(adapted, is_not(none()))
		assert_that(adapted, has_property('key', 'user1@bar'))
		assert_that(adapted, has_property('value', 'IS_FRIEND_OF,user2@bar'))

	@WithMockDSTrans
	def test_user_blog(self):
		user = self._create_user("user1@bar")
		blog = frm_interfaces.IPersonalBlog(user)
		entry = PersonalBlogEntry()
		entry.creator = user
		entry.tags = (IPlainTextContentFragment('bankai'), IPlainTextContentFragment('shikai'))
		blog['bleach'] = entry
		entry.__parent__ = blog
		entry.lastModified = 42
		entry.createdTime = 24

		comment = PersonalBlogComment()
		comment.creator = user
		entry['comment316072059'] = comment
		comment.__parent__ = entry
		comment.createdTime = comment.lastModified = 43
		mock_dataserver.current_transaction.add(comment)

		labels = graph_interfaces.ILabelAdapter(entry, None)
		assert_that(labels, is_not(none()))
		assert_that(labels, has_length(3))
		assert_that(labels, is_((u'bankai', u'shikai', u'topic')))

		props = graph_interfaces.IPropertyAdapter(entry, None)
		assert_that(props, is_not(none()))
		assert_that(props, has_length(7))
		assert_that(props, has_entry('author', u'user1@bar'))
		assert_that(props, has_entry('ntiid', is_not(none())))
		assert_that(props, has_entry('oid', is_not(none())))
		assert_that(props, has_entry('forum', is_not(none())))
		assert_that(props, has_entry('title', u''))
		assert_that(props, has_entry('type', u'Topic'))
		
		labels = graph_interfaces.ILabelAdapter(comment, None)
		assert_that(labels, is_not(none()))
		assert_that(labels, has_length(1))
		assert_that(labels, is_(('comment',)))

		props = graph_interfaces.IPropertyAdapter(comment, None)
		assert_that(props, is_not(none()))
		assert_that(props, has_length(5))
		assert_that(props, has_entry('author', u'user1@bar'))
		assert_that(props, has_entry('oid', is_not(none())))
		assert_that(props, has_entry('topic', is_not(none())))
		assert_that(props, has_entry('type', u'Comment'))


