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

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_none
from hamcrest import is_

from nti.dataserver.contenttypes.forums.tests import ForumTestLayer
from nti.app.forums.tests.base_forum_testing import AbstractTestApplicationForumsBaseMixin

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.assessment.tests import RegisterAssignmentLayerMixin
from nti.app.assessment.tests import RegisterAssignmentsForEveryoneLayer

class TestDiscussionsImport( ApplicationLayerTest ):
		
	layer = RegisterAssignmentsForEveryoneLayer	
	#layer = ForumTestLayer
	
	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		component.provideUtility( self.db )
		self.session = self.db.session
	
	def tearDown(self):
		self.session.close()
	
	@WithSharedApplicationMockDS(users=True,testapp=True,default_authenticate=True)
 	def test_discussion_import(self):
		pass
