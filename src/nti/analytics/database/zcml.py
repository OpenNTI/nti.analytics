#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from . import interfaces
from .database import create_database

class IRegisterDB(interface.Interface):
	"""
	The arguments needed for registering a db
	"""
	name = fields.TextLine(title="db name identifier (site)", required=False, default="")
	dburi = fields.TextLine(title="db uri", required=False)
	twophase = fields.Bool(title='two phase commit protocol', required=False, default=False)
	defaultSQLite = fields.Bool(title='default to SQLite', required=False, default=False)

def registerDB(_context, dburi=None, twophase=False, defaultSQLite=False,
				autocommit=False, name=u""):
	"""
	Register an db
	"""

	if not dburi and not defaultSQLite:
		raise ValueError( "Must specify valid database uri" )

	factory = functools.partial(create_database,
								dburi=dburi,
								twophase=twophase,
								defaultSQLite=defaultSQLite,
								autocommit=autocommit)
	utility(_context, provides=interfaces.IAnalyticsDB,
			factory=factory, name=name)


