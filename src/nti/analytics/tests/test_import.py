#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import unittest

from zope import component

from tempfile import mkstemp

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.users import User

from nti.analytics.admin_views import init_db
from nti.analytics.admin_views import init

import nti.testing.base

from nti.analytics.database import interfaces as analytic_interfaces

from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database.metadata import Users

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_none
from hamcrest import is_

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer, WithMockDSTrans

ZCML_STRING = """
<configure	xmlns="http://namespaces.zope.org/zope"
			xmlns:i18n="http://namespaces.zope.org/i18n"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:adb="http://nextthought.com/analytics/database">

	<include package="zope.component" file="meta.zcml" />
	<include package="zope.security" file="meta.zcml" />
	<include package="zope.component" />
	<include package="nti.analytics.database" file="meta.zcml" />
	
	<utility 	component="nti.analytics.entities" 
				provides="nti.analytics.interfaces.IObjectProcessor" 
				name="entities"/>
	
	<configure>
		<adb:registerAnalyticsDB 	defaultSQLite="True"
									dburi="sqlite://"
									twophase="False"
									autocommit="False" />
	</configure>
	
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

class _ImmediateQueueRunner(object):
	
	def put( self, job ):
		return job()

def _get_job_queue():
	return _ImmediateQueueRunner()

nti.analytics.get_job_queue = _get_job_queue

def _to_external_id( obj ):
	return 101 

from nti.analytics import common
common.to_external_ntiid_oid = _to_external_id

def _find_object( ntiid ):
	return User( 'new_user_101' )

from nti.ntiids import ntiids
ntiids.find_object_with_ntiid = _find_object 

class TestImport(nti.testing.base.ConfiguringTestBase):
	
	def setUp(self):
		self.configure_string(ZCML_STRING)
		self.db = component.queryUtility( analytic_interfaces.IAnalyticsDB, name='' )
		self.session = self.db.session
	
	def tearDown(self):
		self.session.close()
	
	def test_import(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )
		
 		init( User( 'new_user_101' ) )		
 		
 		results = self.session.query(Users).all()
 		assert_that( results, has_length( 1 ) )
 		
 		new_user = self.session.query(Users).one()
 		assert_that( new_user.user_ds_id, is_( 101 ) )
 		assert_that( new_user.user_id, is_( 1 ) )
		