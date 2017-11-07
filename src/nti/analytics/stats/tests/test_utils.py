#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

import unittest

import numpy as _numpy

from nti.analytics.stats.utils import get_std_dev


class TestUtils(unittest.TestCase):

    def test_std_dev(self):
        # Empty
        values = None
        std_dev = get_std_dev(values)
        assert_that(std_dev, none())

        values = []
        std_dev = get_std_dev(values)
        assert_that(std_dev, none())

        # Single
        values = [10]
        std_dev = get_std_dev(values)
        assert_that(std_dev, is_(0))

        value_source = range(50)
        values = []
        for val in value_source:
            values.append(val)
            expected_std_dev = get_std_dev(values)
            actual_std_dev = _numpy.std(values)
            is_close = _numpy.isclose(expected_std_dev, actual_std_dev)
            assert_that(is_close)
