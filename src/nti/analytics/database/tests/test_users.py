#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from zope import component

from hamcrest import is_
from hamcrest import none
from hamcrest import has_length
from hamcrest import assert_that

from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.database import AnalyticsDB

from nti.analytics.database import users as db_users

from nti.analytics.database.users import Users
from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.users import update_user_research

class TestUsers(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://', testmode=True )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session
		assert_that( self.db.engine.table_names(), has_length( 59 ) )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db )
		self.session.close()

	def test_users(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )

		fooser = 2001

		db_users.create_user( fooser )

		results = self.session.query(Users).all()
		assert_that( results, has_length( 1 ) )

		new_user = self.session.query(Users).one()
		# Sequence generated
		assert_that( new_user.user_id, is_( 1 ) )
		assert_that( new_user.user_ds_id, is_( fooser ) )
		assert_that( new_user.allow_research, none() )

		# Dupe, but not inserted
		get_or_create_user( fooser )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 1 ) )

		# And passing in just user ids
		db_users.create_user( 42 )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 2 ) )

		# New
		get_or_create_user( 43 )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 3 ) )

		# Save everything we have.
		self.session.commit()

		# Update research field
		update_user_research( fooser, True )
		self.session.query(Users).filter( Users.user_ds_id == fooser ).one()
		assert_that( new_user.user_id, is_( 1 ) )
		assert_that( new_user.user_ds_id, is_( fooser ) )
		assert_that( new_user.allow_research, is_( True ) )

	def test_user_constraints(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )

		# A None user_ds_id is now perfectly valid.
		new_user = Users( user_ds_id=None )
		self.session.add( new_user )
		self.session.flush()

