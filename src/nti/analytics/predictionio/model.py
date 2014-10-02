#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import IPredictionIOApp

DEFAULT_URL = 'http://localhost:8000'

@WithRepr
@EqHash('AppKey')
@interface.implementer(IPredictionIOApp)
class PredictionIOApp(SchemaConfigured):
	createDirectFieldProperties(IPredictionIOApp)

def create_app(appKey, url=DEFAULT_URL):
	url = url or DEFAULT_URL
	result = PredictionIOApp(AppKey=appKey, URL=url)
	return result
