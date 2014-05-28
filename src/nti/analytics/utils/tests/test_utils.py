#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.graphdb import utils
from nti.graphdb import interfaces as graph_interfaces

from nti.graphdb.tests import ConfiguringTestBase

from hamcrest import (assert_that, none, is_, is_not)

class TestUtils(ConfiguringTestBase):

	def test_unique_attribute(self):
		ua = utils.UniqueAttribute("a", "b")
		assert_that(graph_interfaces.IUniqueAttributeAdapter.providedBy(ua), is_(True))

		adapted = graph_interfaces.IUniqueAttributeAdapter(ua, None)
		assert_that(adapted, is_not(none()))

		ub = utils.UniqueAttribute("a", "b")
		assert_that(ua, is_(ub))

		uc = utils.UniqueAttribute("a", "c")
		assert_that(ua, is_not(uc))
