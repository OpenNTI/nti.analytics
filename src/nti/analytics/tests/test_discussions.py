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
from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database import interfaces as analytic_interfaces

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_none
from hamcrest import is_

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestDiscussionsImport( ApplicationLayerTest ):
	
	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		component.getGlobalSiteManager().registerUtility( self.db, analytic_interfaces.IAnalyticsDB )
		self.session = self.db.session

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db, provided=analytic_interfaces.IAnalyticsDB )
		self.session.close()
	
	@WithSharedApplicationMockDS(users=True,testapp=True,default_authenticate=True)
 	def test_discussion_import(self):
		pass
