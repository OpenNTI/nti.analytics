# -*- coding: utf-8 -*-
"""
schema generation installation.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

generation = 55

from zope.generations.generations import SchemaManager

logger = __import__('logging').getLogger(__name__)


class _AnalyticsSchemaManager(SchemaManager):
    """
    A schema manager that we can register as a utility in ZCML.
    """

    def __init__(self):
        super(_AnalyticsSchemaManager, self).__init__(
            generation=generation,
            minimum_generation=generation,
            package_name='nti.analytics.generations')


def evolve(unused_context):
    pass
