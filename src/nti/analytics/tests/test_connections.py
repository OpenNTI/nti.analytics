#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_in
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User
from nti.dataserver.users import FriendsList

from nti.graphdb import connections
from nti.graphdb import relationships
from nti.graphdb.neo4j import database

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.graphdb.tests import ConfiguringTestBase

class TestFriendShips(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(ConfiguringTestBase, cls).setUpClass()
		cls.db = database.Neo4jDB(cls.DEFAULT_URI)

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def _create_random_user(self):
		username = self._random_username()
		user = self._create_user(username)
		return user

	def _create_friendslist(self, owner, name="mycontacts", *friends):
		result = FriendsList(username=name)
		result.creator = owner
		for friend in friends:
			result.addFriend(friend)
		owner.addContainedObject(result)
		return result

	@WithMockDSTrans
	def test_entity_friends(self):
		owner = self._create_user("owner@bar")
		user1 = self._create_user("1foo@bar")
		user2 = self._create_user("2foo@bar")
		user3 = self._create_user("3foo@bar")

		self._create_friendslist(owner, "mycontacts1", user1, user2)
		self._create_friendslist(owner, "mycontacts2", user3)

		result = connections.db_friends(owner)
		assert_that(result, has_length(3))
		for friend in (user1, user2, user3):
			key = connections._Relationship(owner, friend)
			assert_that(key, is_in(result))

		result = connections.db_friends(user3)
		assert_that(result, has_length(0))

	@WithMockDSTrans
	def test_graph_friends(self):
		user1 = self._create_random_user()
		user2 = self._create_random_user()
		user3 = self._create_random_user()
		self._create_friendslist(user1, "mycontacts1", user2, user3)

		# create in grapth
		self.db.create_relationship(user1, user2, relationships.FriendOf())
		self.db.create_relationship(user1, user3, relationships.FriendOf())

		result = connections.graph_friends(self.db, user1)
		assert_that(result, has_length(2))

		user4 = self._create_random_user()
		self._create_friendslist(user1, "mycontacts2", user4)

		result = connections.update_friendships(self.db, user1)
		assert_that(result, has_length(1))

