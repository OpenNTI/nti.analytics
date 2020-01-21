#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import time
import shutil
import tempfile
import unittest

from fudge import patch_object

from six import string_types
from six import integer_types

import zope.testing.cleanup

from zope import interface
from zope import component

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.app.testing.application_webtest import ApplicationTestLayer

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.analytics_database.interfaces import IAnalyticsDB
from nti.analytics_database.interfaces import IAnalyticsDSIdentifier
from nti.analytics_database.interfaces import IAnalyticsIntidIdentifier
from nti.analytics_database.interfaces import IAnalyticsNTIIDIdentifier
from nti.analytics_database.interfaces import IAnalyticsRootContextIdentifier

from nti.analytics_database.database import AnalyticsDB

from nti.analytics.database.root_context import _create_course

from nti.analytics.database import users as db_users
from nti.analytics.database import sessions as db_sessions
from nti.analytics.database import root_context as db_courses

from nti.app.assessment.tests import RegisterAssignmentLayerMixin

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import DSInjectorMixin


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 GCLayerMixin,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.dataserver', 'nti.analytics', 'nti.contentsearch')

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


DEFAULT_INTID = 101

cache = dict()
id_map = dict()


def _do_cache(obj, val):
    id_map[val] = obj
    cache[obj] = val


@interface.implementer(IAnalyticsDSIdentifier)
class TestIdentifier(object):
    """
    Defines ids simply if they are ints,
    or looks for an 'intid' field.
    """

    default_intid = DEFAULT_INTID

    def get_id(self, obj):
        result = None

        # Opt for ds_intid if we're in a mock_ds
        if hasattr(obj, '_ds_intid'):
            result = getattr(obj, '_ds_intid', None)
        # Ok, make something up.
        elif isinstance(obj, (integer_types, string_types)):
            result = obj
        elif hasattr(obj, 'intid'):
            result = getattr(obj, 'intid', None)

        if result is None and obj in cache:
            return cache.get(obj)

        while result is None:
            # We have poor test cleanup; ensure we get unique id
            TestIdentifier.default_intid += 1
            if TestIdentifier.default_intid not in id_map:
                result = TestIdentifier.default_intid
                break

        try:
            # Some objects attempt to access the backing db.
            _do_cache(obj, result)
        except:
            pass
        return result

    def get_object(self, val):
        result = id_map.get(val, None)

        if result is None:
            try:
                # Try casting to int
                result = id_map.get(int(val))
            except ValueError:
                pass

        result = object() if result is None else result

        return result


test_user_ds_id = 78
test_session_id = 1


class AnalyticsTestBase(unittest.TestCase):
    """
    A base class that creates a user and session, as well as mocks out
    getting ids from objects (and vice versa on reverse lookup).
    """

    def setUp(self):
        self.db = AnalyticsDB(dburi='sqlite://', autocommit=True)
        component.getGlobalSiteManager().registerUtility(self.db, IAnalyticsDB)
        self.session = self.db.session

        self.test_identifier = TestIdentifier()
        component.getGlobalSiteManager().registerUtility(self.test_identifier,
                                                         IAnalyticsIntidIdentifier)
        component.getGlobalSiteManager().registerUtility(self.test_identifier,
                                                         IAnalyticsNTIIDIdentifier)
        component.getGlobalSiteManager().registerUtility(self.test_identifier,
                                                         IAnalyticsRootContextIdentifier)

        self.db_user = db_users.create_user(test_user_ds_id)
        user_agent = 'webapp-1.9'
        ip_addr = '156.110.241.13'
        db_sessions.create_session(test_user_ds_id, user_agent,
                                   time.time(), ip_addr)
        self.course_id = 1
        self.course_record = _create_course(self.db, object(), self.course_id)

    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.db)
        session = self.session
        session.close()
        component.getGlobalSiteManager().unregisterUtility(self.test_identifier)


class NTIAnalyticsTestCase(AnalyticsTestBase):
    layer = SharedConfiguringTestLayer


class NTIAnalyticsApplicationTestLayer(ApplicationTestLayer):

    # This was a little strange.  The tests in decorators and workspaces
    # started failing because of a missing db. This was after a test was
    # added to the views. Previously, this setup/teardown only passed.
    # Perhaps there was some layer interaction between the two, or a
    # closed dataserver?

    # Must implement these methods to avoid the super methods from getting
    # called.

    @classmethod
    def setUp(self):
        self.db = AnalyticsDB(dburi='sqlite://', autocommit=True)
        component.getGlobalSiteManager().registerUtility(self.db, IAnalyticsDB)

    @classmethod
    def tearDown(self):
        component.getGlobalSiteManager().unregisterUtility(self.db)

    @classmethod
    def testSetUp(cls, test=None):
        pass

    @classmethod
    def testTearDown(cls):
        pass
