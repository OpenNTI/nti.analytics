#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from sqlalchemy.exc import IntegrityError

from nti.analytics import _execute_job
from nti.analytics import get_analytics_db
from nti.analytics.database.metadata import Users
from nti.analytics.database.database import AnalyticsDB
from nti.dataserver.users import User

# For new objects, this is the default intid stored in the database.
# For subsequent objects, this will increase by one.
DEFAULT_INTID = 101

import nti.testing.base

ZCML_STRING = """
<configure	xmlns="http://namespaces.zope.org/zope"
			xmlns:i18n="http://namespaces.zope.org/i18n"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:adb="http://nextthought.com/analytics/database">

	<include package="zope.component" file="meta.zcml" />
	<include package="zope.security" file="meta.zcml" />
	<include package="zope.component" />
	<include package="nti.analytics.database" file="meta.zcml" />
			 		 
	<configure>
		<adb:registerAnalyticsDB 	defaultSQLite="True"
									dburi="sqlite://"
									twophase="False"
									autocommit="False" />
	</configure>
</configure>

"""

class TestJob(nti.testing.base.ConfiguringTestBase):

	def setUp(self):
		self.configure_string(ZCML_STRING)
		
	def _read_call( self, db ):	
		# Database arg passed in
		session = db.session()
		return session.query(Users).all()		
				
	def _good_call( self, db ) :
		# Modify database
		fooser = User( 'foo1978' )
		db.create_user( fooser )
	
	def _raise_call(self, db ):
		# Dupe user throws
		fooser = User( 'foo1978' )
		db.create_user( fooser )
		
	def _rollback_call(self, db, valid_new_user ):
		# New valid user
		db.create_user( valid_new_user )
		# Dupe user throws
		fooser = User( 'foo1978' )
		db.create_user( fooser )	
	
	def test_job(self):
		db = get_analytics_db()
		session = db.session()
		results = session.query(Users).all()
		assert_that( results, has_length( 0 ) )
		
		# Multiple calls
		_execute_job( self._read_call )
		_execute_job( self._read_call )
		_execute_job( self._read_call )
		
		# Successful insert
		_execute_job( self._good_call )
		results = session.query(Users).all()
		assert_that( results, has_length( 1 ) )
		
		# Raise and rollback
		with self.assertRaises(IntegrityError):
			_execute_job( self._raise_call )
		
		# Raise and rollback with arg
		valid_new_user = 9999
			
		with self.assertRaises(IntegrityError):
			_execute_job( self._rollback_call, valid_new_user=9999 )	
			
		results = session.query(Users).all()
		assert_that( results, has_length( 1 ) )
		
		result = session.query(Users).one()
		assert_that( result.user_id, is_( 1 ) )
		assert_that( result.user_ds_id, is_( DEFAULT_INTID ) )
		

