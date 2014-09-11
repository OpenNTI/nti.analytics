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

cache = dict()
id_map = dict()

def _do_cache( obj, val ):
	cache[obj] = val
	id_map[val] = obj


class TestIdentifier(_Identifier):
	""" Defines ids simply if they are ints, or looks for an 'intid' field. """

	default_intid = DEFAULT_INTID

	@classmethod
	def get_id( cls, obj ):
		result = None

		if obj in cache:
			return cache.get( obj )
		# Opt for ds_intid if we're in a mock_ds
		elif hasattr( obj, '_ds_intid' ):
			result = getattr( obj, '_ds_intid', None )
		# Ok, make something up.
		elif isinstance( obj, ( integer_types, string_types ) ):
			result = obj
		elif hasattr( obj, 'intid' ):
			result = getattr( obj, 'intid', None )

		if result is None:
			result = TestIdentifier.default_intid
			TestIdentifier.default_intid += 1

		_do_cache( obj, result )
		return result

	@classmethod
	def get_object( cls, val ):
		result = id_map.get( val, None )

		if result is None:
			result = object()

		return result

