#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from dolmen.builtins import IDict
from dolmen.builtins import ITuple

from nti.utils import schema as nti_schema

ADD_EVENT = 0
MODIFY_EVENT = 1
REMOVE_EVENT = 2

class IObjectProcessor(interface.Interface):

	def init(uid, db, obj):
		"""
		build relationships for the specified object
		"""
