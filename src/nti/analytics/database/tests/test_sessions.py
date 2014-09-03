#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest
import fudge
import time

from zope import component

from datetime import datetime

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that

from nti.analytics.model import AnalyticsSession

from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.database import AnalyticsDB

from nti.analytics.database.tests import test_user_ds_id

from nti.analytics.database import sessions as db_sessions

from nti.analytics.database.users import Users
from nti.analytics.database.sessions import Sessions
from nti.analytics.database.sessions import CurrentSessions

class TestSessions(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://', testmode=True )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db )
		self.session.close()

	def test_sessions(self):
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 0 ) )

		user = Users( user_ds_id=test_user_ds_id )
		self.session.add( user )
		self.session.flush()

		# Using new generated user_id
		version = '1.9'
		platform = 'webapp'
		ip_addr = '0.1.2.3.4'
		nti_session = AnalyticsSession( timestamp=time.time(), version=version, platform=platform, ip_addr=ip_addr )
		db_sessions.create_session( test_user_ds_id, nti_session )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )

		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, is_( user.user_id ) )
		assert_that( new_session.session_id, is_( 1 ) )
		assert_that( new_session.ip_addr, is_( ip_addr ) )
		assert_that( new_session.platform, is_( platform ) )
		assert_that( new_session.version, is_( version ) )
		assert_that( new_session.start_time, not_none() )
		assert_that( new_session.end_time, none() )

		results = self.session.query(CurrentSessions).all()
		assert_that( results, has_length( 1 ) )

		new_session = self.session.query(CurrentSessions).one()
		assert_that( new_session.user_id, is_( user.user_id ) )
		assert_that( new_session.session_id, is_( 1 ) )

		new_session_id = db_sessions.get_current_session_id( test_user_ds_id )
		assert_that( new_session_id, is_( 1 ) )

		# New session has our new session id
		nti_session = AnalyticsSession( timestamp=time.time(), version=version, platform=platform, ip_addr=ip_addr )
		db_sessions.create_session( test_user_ds_id, nti_session )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 2 ) )

		results = self.session.query(CurrentSessions).all()
		assert_that( results, has_length( 1 ) )

		new_session = self.session.query(CurrentSessions).one()
		assert_that( new_session.user_id, is_( user.user_id ) )
		assert_that( new_session.session_id, is_( 2 ) )

		new_session_id = db_sessions.get_current_session_id( test_user_ds_id )
		assert_that( new_session_id, is_( 2 ) )
