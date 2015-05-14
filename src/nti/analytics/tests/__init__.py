#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import shutil
import tempfile
import time
import unittest

from fudge import patch_object

from six import integer_types, string_types

import zope.testing.cleanup
from zope import component

from nti.dataserver.tests.mock_dataserver import WithMockDS

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.app.testing.application_webtest import ApplicationTestLayer

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database import users as db_users
from nti.analytics.database import sessions as db_sessions
from nti.analytics.database import root_context as db_courses

from nti.app.assessment.tests import RegisterAssignmentLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

from nti.analytics import identifier
from nti.analytics.identifier import _Identifier

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

		# Opt for ds_intid if we're in a mock_ds
		if hasattr( obj, '_ds_intid' ):
			result = getattr( obj, '_ds_intid', None )
		# Ok, make something up.
		elif isinstance( obj, ( integer_types, string_types ) ):
			result = obj
		elif hasattr( obj, 'intid' ):
			result = getattr( obj, 'intid', None )

		if result is None:
			if obj in cache:
				return cache.get( obj )

		if result is None:
			result = TestIdentifier.default_intid
			TestIdentifier.default_intid += 1

		try:
			# Some objects attempt to access the backing db.
			_do_cache( obj, result )
		except:
			pass
		return result

	@classmethod
	def get_object( cls, val ):
		result = id_map.get( val, None )

		if result is None:
			try:
				# Try casting to int
				result = id_map.get( int( val ) )
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
		self.db = AnalyticsDB( dburi='sqlite://' )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session

		self.patches = [
			patch_object( identifier.RootContextId, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier._DSIdentifier, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier._NtiidIdentifier, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier.RootContextId, 'get_object', TestIdentifier.get_object ),
			patch_object( identifier._DSIdentifier, 'get_object', TestIdentifier.get_object ),
			patch_object( identifier._NtiidIdentifier, 'get_object', TestIdentifier.get_object ) ]

		db_users.create_user( test_user_ds_id )
		user_agent = 'webapp-1.9'
		ip_addr = '156.110.241.13'
		db_sessions.create_session( test_user_ds_id, user_agent, time.time(), ip_addr )
		self.course_id = 1
		db_courses.get_root_context_id( self.db, self.course_id, create=True )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db )
		self.session.close()
		for patch in self.patches:
			patch.restore()

class NTIAnalyticsTestCase(AnalyticsTestBase):
	layer = SharedConfiguringTestLayer

class NTIAnalyticsApplicationTestLayer(ApplicationTestLayer):

	@classmethod
	def setUp(cls):
		pass

	@classmethod
	def tearDown(cls):
		pass
