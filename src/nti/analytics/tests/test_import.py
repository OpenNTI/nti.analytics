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

from nti.app.analytics.views import init_db
from nti.app.analytics.views import init

import nti.testing.base

from nti.analytics.database import interfaces as analytic_interfaces

from nti.dataserver import users

from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database.metadata import Users

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_none
from hamcrest import is_

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer, WithMockDSTrans
from nti.app.testing.base import TestBaseMixin
from nti.app.testing.application_webtest import AppTestBaseMixin,ApplicationLayerTest

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

# 	def test_import_user(self):
# 		results = self.session.query(Users).all()
# 		assert_that( results, has_length( 0 ) )
#
#  		init( User( 'new_user_101' ) )
#
#  		results = self.session.query(Users).all()
#  		assert_that( results, has_length( 1 ) )
#
#  		new_user = self.session.query(Users).one()
#  		assert_that( new_user.user_ds_id, is_( 101 ) )
#  		assert_that( new_user.user_id, is_( 1 ) )

