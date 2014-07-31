#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import shutil
import tempfile

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.app.testing.application_webtest import ApplicationTestLayer

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

import zope.testing.cleanup

from zope import component

from nti.analytics.identifier import _Identifier

from six import integer_types, string_types

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


DEFAULT_INTID = 101

class TestIdentifier(_Identifier):
	""" Defines ids simply if they are ints, or looks for an 'intid' field. """

	def __init__(self):
		self.default_intid = DEFAULT_INTID
		self.cache = dict()

	def get_id( self, obj ):
		# Opt for ds_intid if we're in a mock_ds
		result = getattr( obj, '_ds_intid', None )
		if result:
			return result

		# Otherwise, let's check cache
		if obj in self.cache:
			return self.cache.get( obj )

		# Ok, make something up.
		if isinstance( obj, ( integer_types, string_types ) ):
			result = obj
		elif hasattr( obj, 'intid' ):
			result = getattr( obj, 'intid', None )

		if result is None:
			result = self.default_intid
			self.default_intid += 1

		self.cache[obj] = result
		return result

from nti.analytics import identifier
identifier._DSIdentifier.get_id = identifier._NtiidIdentifier.get_id \
= identifier.SessionId.get_id = TestIdentifier().get_id

class ImmediateQueueRunner(object):
	"""A queue that immediately runs the given job."""
	def put( self, job ):
		job()
