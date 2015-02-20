#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import uuid

from nti.analytics.tests import NTIAnalyticsTestCase
from nti.analytics.tests import SharedConfiguringTestLayer
from nti.analytics.tests import NTIAnalyticsApplicationTestLayer

PIOTestCase = NTIAnalyticsTestCase
PIOApplicationTestLayer = NTIAnalyticsApplicationTestLayer

DEFAULT_URI = u'http://localhost:7474/db/data/'

def random_username(self):
    splits = unicode(uuid.uuid4()).split('-')
    username = "%s@%s" % (splits[-1], splits[0])
    return username
