#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from nti.analytics.common import _execute_job

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class TestJob( NTIAnalyticsTestCase ):
	"""
	Tests that a job can be executed.
	"""

	def _call( self, arg1 ):
		return arg1

	@WithMockDSTrans
	def test_job(self):
		# Multiple non-site calls
		result = _execute_job( self._call, 1 )
		assert_that( result, is_( 1 ) )
		result = _execute_job( self._call, 2 )
		assert_that( result, is_( 2 ) )

		# Call with site
		result = _execute_job( self._call, 10, site_name='bleh' )
		assert_that( result, is_( 10 ) )

