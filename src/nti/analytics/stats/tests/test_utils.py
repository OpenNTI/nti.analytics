#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

try:
	import numpy as _numpy
except ImportError:
	_numpy = None

import unittest

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

from nti.analytics.stats.utils import get_std_dev

class TestUtils( unittest.TestCase ):

	def test_std_dev(self):
		# Empty
		values = None
		std_dev = get_std_dev( values )
		assert_that( std_dev, none() )

		values = []
		std_dev = get_std_dev( values )
		assert_that( std_dev, none() )

		# Single
		values = [ 10 ]
		std_dev = get_std_dev( values )
		assert_that( std_dev, is_( 0 ) )

		# Other
		if not _numpy:
			return

		value_source = range( 50 )
		values = []
		for val in value_source:
			values.append( val )
			expected_std_dev = get_std_dev( values )
			actual_std_dev = _numpy.std( values )
			is_close = _numpy.isclose( expected_std_dev, actual_std_dev )
			assert_that( is_close )



