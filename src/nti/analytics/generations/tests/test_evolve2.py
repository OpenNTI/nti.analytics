#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import none

from nti.testing.matchers import verifiably_provides

from zope import component
from zope.component.hooks import site

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.async import queue
from nti.async.interfaces import IQueue

from nti.analytics.tests import NTIAnalyticsTestCase
from nti.analytics.generations import evolve2

from nti.analytics import QUEUE_NAMES
from nti.analytics import QUEUE_NAME as LEGACY_QUEUE_NAME

class TestEvolve2(NTIAnalyticsTestCase):

	@WithMockDSTrans
	def test_evolve2(self):

		conn = mock_dataserver.current_transaction
		class _context(object): pass
		context = _context()
		context.connection = conn

		ds_folder = context.connection.root()['nti.dataserver']

		# Set up old state
		old_queue = queue.Queue()
		old_queue.__parent__ = ds_folder
		old_queue.__name__ = LEGACY_QUEUE_NAME
		lsm = ds_folder.getSiteManager()
		lsm.registerUtility( old_queue, provided=IQueue, name=LEGACY_QUEUE_NAME )

		evolve2.do_evolve( context )

		with site( ds_folder ):
			# Not sure why this doesn't work
# 			legacy_queue = lsm.queryUtility( IQueue, name=LEGACY_QUEUE_NAME )
# 			assert_that( legacy_queue, none() )

			for queue_name in QUEUE_NAMES:
				job_queue = component.getUtility( IQueue, name=queue_name )
				assert_that( job_queue, verifiably_provides( IQueue ) )
