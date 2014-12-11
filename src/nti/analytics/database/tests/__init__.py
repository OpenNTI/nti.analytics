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
import time

from fudge import patch_object

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
from nti.analytics.database import sessions as db_sessions
from nti.analytics.database import root_context as db_courses

from nti.analytics.tests import DEFAULT_INTID
from nti.analytics.tests import TestIdentifier
from nti.analytics.tests import AnalyticsTestBase
from nti.analytics.tests import SharedConfiguringTestLayer
from nti.analytics.tests import NTIAnalyticsTestCase
from nti.analytics.tests import NTIAnalyticsApplicationTestLayer
from nti.analytics.tests import test_user_ds_id
from nti.analytics.tests import test_session_id

AnalyticsTestBase = AnalyticsTestBase
SharedConfiguringTestLayer = SharedConfiguringTestLayer
NTIAnalyticsTestCase = NTIAnalyticsTestCase
NTIAnalyticsApplicationTestLayer = NTIAnalyticsApplicationTestLayer
test_user_ds_id = test_user_ds_id
test_session_id = test_session_id

class MockParent(object):

	def __init__(self, parent, inReplyTo=None, intid=None, containerId=None, children=None, vals=None ):
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
