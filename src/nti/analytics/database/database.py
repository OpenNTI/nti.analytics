#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sqlite3
import pkg_resources

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from metadata import AnalyticsMetadata
from interfaces import IAnalyticsDB

from zope import interface

@interface.implementer(IAnalyticsDB)
class AnalyticsDB(object):
	
	def __init__( self, dburi, twophase=False, autocommit=False ):
		self.dburi = dburi
		self.twophase = twophase
		self.autocommit = autocommit
		self.engine = create_engine(self.dburi, echo=False )
		self.metadata = AnalyticsMetadata( self.engine )

	def get_session(self):
		Session = sessionmaker(bind=self.engine)
		return Session()

def create_database( dburi=None, twophase=False, defaultSQLite=False, autocommit=False ):
	if defaultSQLite:
		data_dir = os.getenv( 'DATASERVER_DATA_DIR' ) or '/tmp'
		data_dir = os.path.expanduser( data_dir )
		data_file = os.path.join( data_dir, 'analytics-sqlite.db' )
		dburi = "sqlite:///%s" % data_file
		
	logger.info( "Creating database at '%s'", dburi )	
	return AnalyticsDB( dburi, twophase, autocommit )

