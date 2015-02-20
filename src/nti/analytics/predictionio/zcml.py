#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import partial

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from .model import create_app
from .model import DEFAULT_URL

from .interfaces import IPredictionIOApp

class IRegisterPredictionIOApp(interface.Interface):
	name = fields.TextLine(title="app name", required=False, default="")
	appKey = fields.TextLine(title="app key", required=True)
	url = fields.TextLine(title="predictionIO url", required=False)
	
def registerPredictionIOApp(_context, appKey, url=DEFAULT_URL, name=u""):
	"""
	Register an PIO app
	"""
	factory = partial(create_app, appKey=appKey, url=url)
	utility(_context, provides=IPredictionIOApp, factory=factory,
			name=name)
