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

from zope import schema
from zope import component
from zope import interface

from zope.component.zcml import utility

from zope.configuration import fields

from nti.dataserver.interfaces import IDataserverClosedEvent

from .database import AnalyticsDB

from .interfaces import IAnalyticsDB

class IRegisterAnalyticsDB(interface.Interface):
	"""
	The arguments needed for registering the analytics db.
	"""
	dburi = fields.TextLine(title="db uri", required=False)
	twophase = schema.Bool(title="twophase commit", required=False)
	autocommit = fields.Bool(title="autocommit", required=False)
	defaultSQLite = schema.Bool(title="default to SQLite", required=False)
	testmode = schema.Bool(title="start the db in test mode", required=False)
	config = fields.TextLine(title="path to config file", required=False)

def registerAnalyticsDB(_context, dburi=None, twophase=False, autocommit=False,
						defaultSQLite=False, testmode=False, config=None):
	"""
	Register the db
	"""
	factory = functools.partial(AnalyticsDB,
								dburi=dburi,
								twophase=twophase,
								autocommit=autocommit,
								defaultSQLite=defaultSQLite,
								testmode=testmode,
								config=config)
	utility(_context, provides=IAnalyticsDB, factory=factory)

# Should only be called in testmode. Resets our in-memory database.
@component.adapter(IDataserverClosedEvent)
def _closed_dataserver(event):
	# This dupes what we have in config.zcml.
	logger.info('Resetting AnalyticsDB')
	db = AnalyticsDB(dburi='sqlite://', testmode=True, defaultSQLite=True)
	component.getSiteManager().registerUtility(db, IAnalyticsDB)
