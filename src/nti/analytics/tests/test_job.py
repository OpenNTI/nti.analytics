#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.analytics import _execute_job
from nti.analytics.database import get_analytics_db
from nti.analytics.database import users as db_users
from nti.analytics.database.users import Users

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

	def _read_call( self ):
		db = get_analytics_db()
		session = db.session()
		return session.query(Users).all()

	def _good_call(self, valid_new_user ):
		db_users.create_user( valid_new_user )

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
		valid_new_user = 9999
		_execute_job( self._good_call, valid_new_user=valid_new_user )
		results = session.query(Users).all()
		assert_that( results, has_length( 1 ) )

		result = session.query(Users).one()
		assert_that( result.user_id, is_( 1 ) )
		assert_that( result.user_ds_id, is_( valid_new_user ) )

