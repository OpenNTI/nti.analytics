#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import unittest

from datetime import datetime

from tempfile import mkstemp

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from ..metadata import Users
from ..metadata import Sessions
from ..metadata import ChatsInitiated

from ..database import create_database

from sqlalchemy.orm.exc import FlushError

test_user_id = 01234
test_session_id = 56

class TestUsers(unittest.TestCase):

	def setUp(self):
		_, self.filename = mkstemp()
		uri = 'sqlite:///%s' % self.filename
		self.db = create_database( dburi=uri )
		assert_that( self.db.engine.table_names(), has_length( 24 ) )
		
		self.session = self.db.get_session()
		
	def tearDown(self):
		os.remove( self.filename )
				
	def test_users(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )
		
		user = Users( user_id=test_user_id, username='Oberyn Martell' )
		self.session.add( user )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 1 ) )
		
		new_user = self.session.query(Users).one()
		assert_that( new_user.user_id, test_user_id )
		assert_that( new_user.user_id, 'Oberyn Martell' )
		assert_that( new_user.email, none() )

		with self.assertRaises(FlushError):
			user2 = Users( user_id=test_user_id, username='Oberyn Martell' )
			self.session.add( user2 )
			self.session.commit()
		
	def test_sessions(self):
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 0 ) )
		
		user = Users( user_id=01234, username='Oberyn Martell' )
		self.session.add( user )
		
		new_session = Sessions( session_id=test_session_id, user_id=test_user_id, ip_addr='0.1.2.3.4', version='webapp-0.9', timestamp=datetime.now() )
		self.session.add( new_session )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )
		
		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, test_user_id )
		assert_that( new_session.session_id, test_session_id )
		assert_that( new_session.ip_addr, '0.1.2.3.4' )	
		assert_that( new_session.version, 'webapp-0.9' )	

class TestAnalytics(unittest.TestCase):

	def setUp(self):
		_, self.filename = mkstemp()
		uri = 'sqlite:///%s' % self.filename
		self.db = create_database( dburi=uri )
		assert_that( self.db.engine.table_names(), has_length( 24 ) )
		
		self.session = self.db.get_session()
		user = Users( user_id=test_user_id, username='test_user1' )
		self.session.add( user )
		
		db_session = Sessions( session_id=test_session_id, user_id=01234, ip_addr='0.1.2.3.4', version='webapp-0.9', timestamp=datetime.now() )
		self.session.add( db_session )
		
	def tearDown(self):
		os.remove( self.filename )
		
	def test_chats(self):
		results = self.session.query( ChatsInitiated ).all()
		assert_that( results, has_length( 0 ) )
		
		new_chat = ChatsInitiated( session_id=test_session_id, user_id=test_user_id, timestamp=datetime.now() )
		self.session.add( new_chat )
		results = self.session.query(ChatsInitiated).all()
		assert_that( results, has_length( 1 ) )
		
		new_chat = self.session.query(ChatsInitiated).one()
		assert_that( new_chat.user_id, test_user_id )
		assert_that( new_chat.session_id, test_session_id )
		assert_that( new_chat.timestamp, 0 )	
	

