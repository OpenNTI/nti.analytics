#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest
import time

from zope import component

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import less_than_or_equal_to

from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.database import AnalyticsDB

from nti.analytics.database.tests import test_user_ds_id

from nti.analytics.database import sessions as db_sessions

from nti.analytics.database.users import Users
from nti.analytics.database.sessions import Sessions
from nti.analytics.database.sessions import UserAgents
from nti.analytics.database.sessions import IpGeoLocation
from nti.analytics.database.sessions import _check_ip_location

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
		results = self.session.query(UserAgents).all()
		assert_that( results, has_length( 0 ) )

		user = Users( user_ds_id=test_user_ds_id )
		self.session.add( user )
		self.session.flush()

		# Using new generated user_id
		user_agent = 'webapp-1.9'
		ip_addr = '156.110.241.13'
		db_sessions.create_session( test_user_ds_id, user_agent, time.time(), ip_addr )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )

		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, is_( user.user_id ) )
		assert_that( new_session.session_id, is_( 1 ) )
		assert_that( new_session.ip_addr, is_( ip_addr ) )
		assert_that( new_session.user_agent_id, is_( 1 ) )
		assert_that( new_session.start_time, not_none() )
		assert_that( new_session.end_time, none() )

		results = self.session.query(UserAgents).all()
		assert_that( results, has_length( 1 ) )

		user_agent_record = results[0]
		assert_that( user_agent_record.user_agent, is_( user_agent ) )
		assert_that( user_agent_record.user_agent_id, is_( 1 ) )

		# New session has our new session id, same user_agent
		db_sessions.create_session( test_user_ds_id, user_agent, time.time(), ip_addr )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 2 ) )

		results = self.session.query(UserAgents).all()
		assert_that( results, has_length( 1 ) )

		# Different user_agent
		user_agent2 = 'ipad-blahblah'
		db_sessions.create_session( test_user_ds_id, user_agent2, time.time(), ip_addr )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 3 ) )

		results = self.session.query(UserAgents).all()
		assert_that( results, has_length( 2 ) )

		# End session
		new_session_id = 3
		db_sessions.end_session( test_user_ds_id, new_session_id, timestamp=time.time() )

		current_session = self.session.query(Sessions).filter( Sessions.session_id == new_session_id ).first()
		assert_that( current_session, not_none() )
		assert_that( current_session.end_time, not_none() )

	def test_large_user_agent(self):
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query(UserAgents).all()
		assert_that( results, has_length( 0 ) )

		user = Users( user_ds_id=test_user_ds_id )
		self.session.add( user )
		self.session.flush()

		# Using new generated user_id
		# Massive user_agent (over 512)
		user_agent = 'webapp-1.9' * 100
		assert_that( user_agent, has_length( greater_than( 512 )))
		ip_addr = '156.110.241.13'
		db_sessions.create_session( test_user_ds_id, user_agent, time.time(), ip_addr )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )

		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, is_( user.user_id ) )
		assert_that( new_session.session_id, is_( 1 ) )
		assert_that( new_session.ip_addr, is_( ip_addr ) )
		assert_that( new_session.user_agent_id, is_( 1 ) )
		assert_that( new_session.start_time, not_none() )
		assert_that( new_session.end_time, none() )

		results = self.session.query(UserAgents).all()
		assert_that( results, has_length( 1 ) )

		user_agent_record = results[0]
		assert_that( user_agent_record.user_agent, has_length( less_than_or_equal_to( 512 )) )
		assert_that( user_agent_record.user_agent_id, is_( 1 ) )

	def test_ip_geolocation(self):
		results = self.session.query(IpGeoLocation).all()
		assert_that( results, has_length( 0 ) )

		ip_addr = '156.110.241.13' # alpha
		_check_ip_location( self.db, ip_addr, test_user_ds_id )

		results = self.session.query(IpGeoLocation).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].country_code, is_( 'US' ))
		assert_that( results[0].latitude, not_none())
		assert_that( results[0].longitude, not_none())

		# Dupe for user does not add
		_check_ip_location( self.db, ip_addr, test_user_ds_id )

		results = self.session.query(IpGeoLocation).all()
		assert_that( results, has_length( 1 ) )
