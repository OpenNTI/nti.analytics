#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from dolmen.builtins import IDict
from dolmen.builtins import IString

from nti.schema.field import ValidTextLine

class IPredictionIOApp(interface.Interface):
	AppKey = ValidTextLine(title='application key')
	URL = ValidTextLine(title='application URL')

class IProperties(IDict):
	pass

class IType(IString):
	pass

class IOID(IString):
	pass
