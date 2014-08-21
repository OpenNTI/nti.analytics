#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import shutil
import tempfile
import unittest

from datetime import datetime

from zope import component
import zope.testing.cleanup

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.app.testing.application_webtest import ApplicationTestLayer

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

from nti.analytics import identifier
from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database import users as db_users

from nti.analytics.tests import DEFAULT_INTID

from nti.analytics.tests import TestIdentifier
identifier._DSIdentifier.get_id = identifier._NtiidIdentifier.get_id \
= identifier.SessionId.get_id = TestIdentifier().get_id

class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 GCLayerMixin,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.dataserver', 'nti.analytics')

    @classmethod
    def setUp(cls):
        cls.setUpPackages()
        cls.old_data_dir = os.getenv('DATASERVER_DATA_DIR')
        cls.new_data_dir = tempfile.mkdtemp(dir="/tmp")
        os.environ['DATASERVER_DATA_DIR'] = cls.new_data_dir

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        cls.setUpTestDS(test)
        shutil.rmtree(cls.new_data_dir, True)
        os.environ['DATASERVER_DATA_DIR'] = cls.old_data_dir or '/tmp'

    @classmethod
    def testTearDown(cls):
        pass

import unittest

class NTIAnalyticsTestCase(unittest.TestCase):
    layer = SharedConfiguringTestLayer

class NTIAnalyticsApplicationTestLayer(ApplicationTestLayer):

    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

class MockParent(object):

	def __init__(self, parent, inReplyTo=None, intid=None, containerId=None, children=None, vals=None, description=None, body=None):
		self.__parent__ = parent
		self.inReplyTo = inReplyTo
		self.intid = intid
		self.containerId = containerId
		self.children = children if children else list()
		self.vals = vals
		self.description = 'new description'
		self.body = ['test_content',]

	def values(self):
		return self.children

	def __iter__(self):
		return iter(self.vals)

test_user_ds_id = 78
test_session_id = '56'

class AnalyticsTestBase(unittest.TestCase):
	""" A base class that simply creates a user and session"""

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session
		db_users.create_user( test_user_ds_id )
		db_users.create_session( test_user_ds_id, test_session_id, datetime.now(), '0.1.2.3.4', 'webapp', '0.9' )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db )
		self.session.close()
