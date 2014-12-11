#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics.database import Base

class AnalyticsMetadata(object):

	def __init__(self, engine):
		logger.info( "Initializing database" )
		Base.metadata.create_all(engine)

