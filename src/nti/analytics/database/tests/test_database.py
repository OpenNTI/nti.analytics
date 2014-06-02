#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from ..metadata import Users

from ..database import create_database

class TestAnalytics(unittest.TestCase):

	def setUp(self):
		self.db = create_database( defaultSQLite=True )
		assert_that( self.db.engine.table_names(), has_length( 24 ) )

	def test_insert(self):
		session = self.db.get_session()
		
		results = session.query(Users).all()
		assert_that( results, has_length( 0 ) )
		
		user = Users( user_id=01234, username='Oberyn Martell' )
		session.add( user )
		results = session.query(Users).all()
		assert_that( results, has_length( 1 ) )
		
		new_user = session.query(Users).one()
		assert_that( new_user.user_id, 01234 )
		assert_that( new_user.user_id, 'Oberyn Martell' )
	

