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

from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import MetaData
from sqlalchemy import ForeignKey
from sqlalchemy import Boolean
from sqlalchemy import Enum
from sqlalchemy import DateTime

def _session_column():
	return Column('session_id', Integer, ForeignKey("sessions.session_id") )
	
def _user_column():
	return Column('user_id', Integer, ForeignKey("users.user_id") )

def _timestamp_column():
	return Column('timestamp', DateTime)

def _course_column():
	return Column('course_id', String(64) )

def _time_length_column():
	return Column('time_length', Integer)

def _context_path_column():
	return Column('context_path', String(1048))

def _resource_column():
	return Column('resource_id', String(1048))

def _assignment_column():
	return Column('assignment_id', String(1048))

def _social_columns():
	return [ _session_column(), _user_column(), _timestamp_column() ]



class AnalyticsMetadata(object): 

	def __init__(self):
		self.metadata = MetaData()
		#TODO Better way to do this?
		self.users
		self.sessions
		self.chats_initiated
		self.chats_joined
		self.groups_created
		self.distibution_lists_created
		self.contacts_added
		self.contacts_removed
		self.thoughts_created
		self.thoughts_viewed
		self.course_resource_views
		self.video_events
		self.notes_created
		self.notes_viewed
		self.highlights_created
		self.forums_created
		self.discussions_created
		self.discussions_viewed
		self.comments_created
		self.course_catalog_views
		self.course_enrollments
		self.course_drops
		self.assignments_taken
		self.assignment_details


	## TODO LIST
	#	examine String limits
	#		TODO Should we use TEXT instead of String?
	#	parent id (comments, replies, etc)
	#	indexes
	#	sequence
	#	constraint

	# TODO uid should come from DS
	# 	if so, we don't need any other identification, or this table perhaps
	#	if not, we should map the DS id to a obfuscated id here.

	# Timestamps TEXT here?

	@property
	def users(self):
		return Table(	'users', self.metadata,
	    				Column('user_id', Integer, primary_key=True),
	    	   			Column('username', String(64), nullable=False) )
		
	# TODO timezone?	
		
	@property
	def sessions(self):
		return Table(	'sessions', self.metadata,
	    				Column('session_id', Integer, primary_key=True),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			Column('ip_addr', String(64) ),
	    	   			Column('version', String(64) ) )	
	
	# TODO combo keys here?
	# TODO how about inverse here? (contact_removed, groups_destroyed?)
	# TODO do social elements have course context?
	# This information needs to be obscured to protect privacy.	

	
	@property
	def chats_initiated(self):
		return Table( 'chats_initiated', self.metadata, *_social_columns() )	
		
	@property
	def chats_joined(self):
		return Table( 'chats_joined', self.metadata, *_social_columns() )	
		
	@property
	def groups_created(self):
		return Table( 'groups_created', self.metadata, *_social_columns() )	
		
	@property
	def distibution_lists_created(self):
		return Table( 'distibution_lists_created', self.metadata, *_social_columns() )	
	
	@property
	def contacts_added(self):
		return Table( 'contacts_added', self.metadata, *_social_columns() )	
	
	@property
	def contacts_removed(self):
		return Table( 'contacts_removed', self.metadata, *_social_columns() )	
	
	@property
	def thoughts_created(self):
		return Table( 'thoughts_created', self.metadata, *_social_columns() )	
	
	@property
	def thoughts_viewed(self):
		return Table( 'thoughts_viewed', self.metadata, *_social_columns() )				
	
	
	
	# For meta-views into synthetic course info, we can special type:
	#	(about|instructors|tech_support)	
	@property
	def course_resource_views(self):
		return Table(	'course_resource_views', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			_resource_column(),
	    	   			_time_length_column(),
	    	   			_context_path_column() )	
	
	# TODO Would we query on these separate event types? Probably not.
	# 	If so, we may break them out into separate tables.	
	# TODO how about calculating the intervals?
	@property
	def video_events(self):
		return Table(	'video_events', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			_resource_column(),
	    	   			Column('video_event_type', Enum( 'WATCH', 'SKIP' ) ),
	    	   			Column('video_start_time', DateTime ),
	    	   			Column('video_end_time', DateTime ),
	    	   			Column('with_transcript', Boolean ),
	    	   			_context_path_column() )	
		
	@property
	def notes_created(self):
		return Table(	'notes_created', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			_resource_column(),
	    	   			Column('sharing', String(16) ) ) #PUBLIC|PRIVATE|COURSE_ONLY	
		
	@property
	def notes_viewed(self):
		return Table(	'notes_viewed', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			_resource_column() )
		
	@property
	def highlights_created(self):
		return Table(	'highlights_created', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			_resource_column() )		
		
	
	
	@property
	def forums_created(self):
		return Table(	'forums_created', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			Column('forum_id', String(256), primary_key=True ) )					
	
	@property
	def discussions_created(self):
		return Table(	'discussions_created', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			Column('forum_id', String(256), ForeignKey("forums_created.forum_id") ),
	    	   			Column('discussion_id', String(256), primary_key=True ) )		
		
	@property
	def discussions_viewed(self):
		return Table(	'discussions_viewed', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			Column('forum_id', String(256), ForeignKey("forums_created.forum_id") ),
	    	   			Column('discussion_id', String(256), ForeignKey("discussions_created.discussion_id") ),
	    	   			_time_length_column() )		
		
	@property
	def comments_created(self):
		return Table(	'comments_created', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			Column('forum_id', String(256), ForeignKey("forums_created.forum_id") ),
	    	   			Column('discussion_id', String(256), ForeignKey("discussions_created.discussion_id") ) )		
		
		
		
	@property
	def course_catalog_views(self):
		return Table(	'course_catalog_views', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column() )
		
		
	
	# TODO Do we want instructors here at all?
	#	If not, we just have for_credit and non_credit		
	# Is dropped redundant?  It may be useful to grab all course enrollment information here.		
	@property
	def course_enrollments(self):
		return Table(	'course_enrollments', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			Column('for_credit', Boolean ),
	    	   			Column('dropped', Boolean ) )	
		
	@property
	def course_drops(self):
		return Table(	'course_drops', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column() )	
		
		
	# Self-assessments too				
	# Self-assessments may have retakes; so may assignments.	
	# TODO Should feedback have its own event tracking?
	@property
	def assignments_taken(self):
		return Table(	'assignments_taken', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			_time_length_column(),
	    	   			_assignment_column(),
	    	   			Column('grade', String(256)),
	    	   			Column('feedback_count', Integer) )
	
	# TODO How do we do this with retakes, is it important to distinguish?		
	#	Perhaps we need to generate a unique id here that maps to assignment_details.
	# TODO Can we rely on these parts/ids being integers?
	@property
	def assignment_details(self):
		return Table(	'assignment_details', self.metadata,
	    				_session_column(),
	    	   			_user_column(),
	    	   			_timestamp_column(),
	    	   			_course_column(),
	    	   			_time_length_column(),
	    	   			_assignment_column(),
	    	   			Column('question_id', Integer),
	    	   			Column('question_part', Integer),
	    	   			Column('submission', String(1048)), #(Freeform|MapEntry|Index|List)
	    	   			Column('is_correct', Boolean) )	
	
	
	def initialize( self, engine ):
		logger.info( "Initializing database" )	
		self.metadata.create_all( engine )
		
		