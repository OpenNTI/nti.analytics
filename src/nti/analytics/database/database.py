#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

import zope.intid
from zope import interface
from zope.sqlalchemy import ZopeTransactionExtension

from nti.utils.property import Lazy

from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.metadata import AnalyticsMetadata


def create_course(course):
	db = get_analytics_db()
	# We may have non-IUsers here, but let's keep them since we may need
	# them (e.g. community owned forums).
	username = getattr( user, 'username', None )
	uid = _userid.get_id( user )

	user = Users( user_ds_id=uid )
	# We'd like to use 'merge' here, but we cannot (in sqlite) if our primary key
	# is a sequence.
	# For race conditions, let's just throw since we cannot really handle retrying
	# gracefully at this level. A job-level retry should work though.
	db.session.add( user )
	db.session.flush()
	logger.info( 'Created user (user=%s) (user_id=%s) (user_ds_id=%s)', username, user.user_id, uid )
	return user

def get_or_create_user(user):
	db = get_analytics_db()
	uid = _userid.get_id( user )
	found_user = db.session.query(Users).filter( Users.user_ds_id == uid ).first()
	return found_user or create_user( user )


@interface.implementer(IAnalyticsDB)
class AnalyticsDB(object):

	pool_size = 30
	max_overflow = 10
	pool_recycle = 300

	def __init__( self, dburi=None, twophase=False, autocommit=False, defaultSQLite=False, testmode=False, config=None ):
		self.dburi = dburi
		self.twophase = twophase
		self.autocommit = autocommit
		self.testmode = testmode

		if defaultSQLite and not dburi:
			data_dir = os.getenv( 'DATASERVER_DATA_DIR' ) or '/tmp'
			data_dir = os.path.expanduser( data_dir )
			data_file = os.path.join( data_dir, 'analytics-sqlite.db' )
			self.dburi = "sqlite:///%s" % data_file
		elif config:
			config_name = os.path.expandvars(config)
			parser = ConfigParser.ConfigParser()
			parser.read([config_name])
			if parser.has_option('analytics', 'dburi'):
				self.dburi = parser.get('analytics', 'dburi')
			if parser.has_option('analytics', 'twophase'):
				self.twophase = parser.getboolean('analytics', 'twophase')
			if parser.has_option('analytics', 'autocommit'):
				self.autocommit = parser.getboolean('analytics', 'autocommit')

		logger.info( "Connecting to database at '%s'", self.dburi )
		self.metadata = AnalyticsMetadata( self.engine )

	@Lazy
	def engine(self):
		try:
			if self.dburi == 'sqlite://':
				# In-memory connections have a different db per connection, so let's make
				# them share a db connection to avoid missing metadata issues.
				# Only for devmode.
				result = create_engine(	self.dburi,
                   				connect_args={'check_same_thread':False},
                   	    		poolclass=StaticPool )

			else:
				result = create_engine(self.dburi,
							   	   pool_size=self.pool_size,
							   	   max_overflow=self.max_overflow,
							   	   pool_recycle=self.pool_recycle)
		except TypeError:
			# SQLite does not use pooling anymore.
			result = create_engine( self.dburi )
		return result

	@Lazy
	def sessionmaker(self):
		if self.autocommit or self.testmode:
			result = sessionmaker(bind=self.engine,
							  	  twophase=self.twophase)
		else:
			# Use the ZTE for transaction handling.
			result = sessionmaker(bind=self.engine,
								  autoflush=True,
							  	  twophase=self.twophase,
							  	  extension=ZopeTransactionExtension() )

		return result

	@Lazy
	def session(self):
		# This property proxies into a thread-local session.
		return scoped_session( self.sessionmaker )

