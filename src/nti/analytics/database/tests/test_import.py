#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import unittest

from tempfile import mkstemp

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.users import User

from nti.analytics.admin_views import init_db
from nti.analytics.admin_views import init

import nti.testing.base

from ..database import AnalyticsDB
from ..metadata import Users

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_property

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer, WithMockDSTrans

ZCML_STRING = """
<configure	xmlns="http://namespaces.zope.org/zope"
			xmlns:i18n="http://namespaces.zope.org/i18n"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:adb="http://nextthought.com/analytics/database">

	<include package="zope.component" file="meta.zcml" />
	<include package="zope.security" file="meta.zcml" />
	<include package="zope.component" />
	
	<utility component="nti.analytics.entities" provides="nti.analytics.interfaces.IObjectProcessor" name="entities"/>
	
</configure>
"""
# 
# class TestImportFromDS(ApplicationLayerTest):
# 	@WithSharedApplicationMockDS(users=True,testapp=True,default_authenticate=True)
# 	def test_import(self):
# 		
# 		#sj = 'sjohnson@nextthought.com'
# 		
# 		# ComponentLookupError: (<InterfaceClass zope.intid.interfaces.IIntIds>, '')?
# 		# Mock DS does not have this component?
# 		#init_db( self.db, usernames=[sj] )
# 		
# 		uid = 01
# 		entity = user1 = User.create_user( self.ds, username='foo@bar' )
# 		init( uid, self.db, entity )
		
# class TestImportFromDS(unittest.TestCase):
# 
# 	layer = SharedConfiguringTestLayer
# 	
# 	def setUp(self):
#  		_, self.filename = mkstemp()
# 		uri = 'sqlite:///%s' % self.filename
# 		self.db = AnalyticsDB( dburi=uri )	
# 
# 	@WithMockDSTrans
# 	def test_import(self):
# 		session = self.db.get_session()
# 		results = session.query(Users).all()
# 		assert_that( results, has_length( 0 ) )
# 		#sj = 'sjohnson@nextthought.com'
# 		
# 		# ComponentLookupError: (<InterfaceClass zope.intid.interfaces.IIntIds>, '')?
# 		# Mock DS does not have this component?
# 		#init_db( self.db, usernames=[sj] )
# 		
# 		uid = 01
# 		entity = User.create_user( self.ds, 'foo@bar' )
# 		init( uid, self.db, entity )		
# 		
# 		session = self.db.get_session()
# 		results = session.query(Users).all()
# 		assert_that( results, has_length( 1 ) )

class TestImport(nti.testing.base.ConfiguringTestBase):
	
	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		self.session = self.db.session
		self.configure_string(ZCML_STRING)
	
	def tearDown(self):
		self.session.close()
	
	def test_import(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )
		
		
	# TODO Need to mock queueing	
# 		init( self.db, User( username='test@nextthought' ) )		
# 		
# 		results = self.session.query(Users).all()
# 		assert_that( results, has_length( 1 ) )
# 		
# 		new_user = self.session.query(Users).one()
# 		assert_that( new_user, has_property( 'user_ds_id', uid ) )
# 		assert_that( new_user, has_property( 'user_id' ), 1 )
		