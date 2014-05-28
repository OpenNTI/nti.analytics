#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.users import User

from nti.dataserver.contenttypes import Note

from nti.graphdb.neo4j import database

from nti.ntiids.ntiids import make_ntiid

from nti.graphdb.tests import ConfiguringTestBase

class TestRatings(ConfiguringTestBase):

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

	def _create_note(self, msg, creator, containerId=None):
		note = Note()
		note.body = [unicode(msg)]
		note.creator = creator
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note


