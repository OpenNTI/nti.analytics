#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.analytics.tests import DEFAULT_INTID
from nti.analytics.tests import TestIdentifier
from nti.analytics.tests import AnalyticsTestBase
from nti.analytics.tests import NTIAnalyticsTestCase
from nti.analytics.tests import SharedConfiguringTestLayer
from nti.analytics.tests import NTIAnalyticsApplicationTestLayer

from nti.analytics.tests import test_user_ds_id
from nti.analytics.tests import test_session_id


class MockParent(object):

    def __init__(self, parent, inReplyTo=None, intid=None,
                 containerId=None, children=None, vals=None):
        self.vals = vals
        self.intid = intid
        self.__parent__ = parent
        self.inReplyTo = inReplyTo
        self.containerId = containerId
        self.body = [u'test_content',]
        self.description = u'new description'
        self.children = children if children else list()

    def values(self):
        return self.children

    def __iter__(self):
        return iter(self.vals)
