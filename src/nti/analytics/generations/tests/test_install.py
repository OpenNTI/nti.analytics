#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from nti.testing.matchers import verifiably_provides

from zope.component.hooks import site
from zope.event import notify

from zope import component

from nti.dataserver.tests import mock_dataserver

from nti.async import queue
from nti.async import interfaces as asyc_interfaces

from nti.analytics import QUEUE_NAME

from nti.analytics.tests import NTIAnalyticsTestCase

class TestInstall(NTIAnalyticsTestCase):

	@mock_dataserver.WithMockDSTrans
	def test_install(self):
		job_queue = component.getUtility( asyc_interfaces.IQueue, name=QUEUE_NAME )
		assert_that( job_queue, verifiably_provides( asyc_interfaces.IQueue ) )
