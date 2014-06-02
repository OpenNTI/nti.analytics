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

from metadata import Users
from metadata import Sessions
from metadata import ChatsInitiated
from metadata import ChatsJoined
from metadata import GroupsCreated
from metadata import DistributionListsCreated
from metadata import ContactsAdded
from metadata import ContactsRemoved
from metadata import ThoughtsCreated
from metadata import ThoughtsViewed
from metadata import CourseResourceViews
from metadata import VideoEvents
from metadata import NotesCreated
from metadata import NotesViewed
from metadata import HighlightsCreated
from metadata import ForumsCreated
from metadata import DiscussionsCreated
from metadata import DiscussionsViewed
from metadata import CommentsCreated
from metadata import CourseCatalogViews
from metadata import CourseEnrollments
from metadata import CourseDrops
from metadata import AssignmentsTaken
from metadata import AssignmentDetails
from metadata import SelfAssessmentsTaken

# We should only have a few different types of operations here:
# - Insertions
# - Deleted objects will modify 'deleted' column with timestamp
# - Reads


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
	
	def create_user(self,session,user):
		user = Users( user_id=user.intid, username=user.username, email=user.email )
		session.add( user )
		
	def create_session(self,session,user,nti_session,ip_address,version):
		#TODO what objects will we have?
		new_session = Sessions( user_id=user.intid, session_id=nti_session.intid, timestamp=nti_session.timestamp, ip_addr=ip_address, version=version )
		session.add( new_session )		
		
	def create_chat_initated(self,session,user,timestamp):
		new_object = ChatsInitiated( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )		
		
	def create_chat_joined(self,session,user,timestamp):
		new_object = ChatsJoined( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )	
		
	def create_groups(self,session,user,timestamp):
		new_object = GroupsCreated( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )	
		
	def create_distribution_lists(self,session,user,timestamp):
		new_object = DistributionListsCreated( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )	
		
	def create_contacts_added(self,session,user,timestamp):
		new_object = ContactsAdded( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )	
		
	def create_contacts_removed(self,session,user,timestamp):
		new_object = ContactsRemoved( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )	
		
	def create_thoughts(self,session,user,timestamp):
		new_object = ThoughtsCreated( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )	
		
	def create_thoughts_viewed(self,session,user,timestamp):
		new_object = ThoughtsViewed( user_id=user.intid, session_id=nti_session.intid, timestamp=timestamp )
		session.add( new_object )				
		
		
		

	#StudentParticipationReport	
	def get_comments_for_user(self, session, user, course_id):		
		results = session.query(CommentsCreated).filter( user_id=user.intid, course_id=course_id, deleted=None ).all()
		return results
	
	def get_discussions_created_for_user(self, session, user, course_id):		
		results = session.query(DiscussionsCreated).filter( user_id=user.intid, course_id=course_id, deleted=None  ).all()
		return results
	
	def get_self_assessments_for_user(self, session, user, course_id):		
		results = session.query(SelfAssessmentsTaken).filter( user_id=user.intid, course_id=course_id ).all()
		return results
	
	def get_assignments_for_user(self, session, user, course_id):		
		results = session.query(AssignmentsTaken).filter( user_id=user.intid, course_id=course_id ).all()
		return results
	
	#TopicReport
	def get_comments_for_discussion(self, session, discussion_id):
		results = session.query(CommentsCreated).filter( discussion_id=discussion_id ).all()
		return results
	
	#ForumReport
	def get_comments_for_forum(self, session, forum_id):
		results = session.query(CommentsCreated).filter( forum_id=forum_id, deleted=None  ).all()
		return results
	
	def get_discussions_created_for_forum(self, session, forum_id):		
		results = session.query(DiscussionsCreated).filter( forum_id=forum_id, deleted=None  ).all()
		return results
	
	#CourseReport
	def get_comments_for_course(self, session, course_id):
		results = session.query(CommentsCreated).filter( course_id=course_id, deleted=None  ).all()
		return results
	
	def get_discussions_created_for_course(self, session, course_id):		
		results = session.query(DiscussionsCreated).filter( course_id=course_id, deleted=None  ).all()
		return results
	
	def get_self_assessments_for_course(self, session, course_id):		
		results = session.query(SelfAssessmentsTaken).filter( course_id=course_id ).all()
		return results
	
	def get_assignments_for_course(self, session, course_id):		
		results = session.query(AssignmentsTaken).filter( course_id=course_id ).all()
		return results
	
	def get_notes_created_for_course(self, session, course_id):		
		results = session.query(NotesCreated).filter( course_id=course_id, deleted=None  ).all()
		return results
	
	def get_highlights_created_for_course(self, session, course_id):		
		results = session.query(HighlightsCreated).filter( course_id=course_id, deleted=None  ).all()
		return results
	
	#AssignmentReport
	def get_assignment_details_for_course(self, session, course_id):		
		results = session.query(AssignmentDetails).filter( course_id=course_id ).all()
		return results

def create_database( dburi=None, twophase=False, defaultSQLite=False, autocommit=False ):
	if defaultSQLite:
		data_dir = os.getenv( 'DATASERVER_DATA_DIR' ) or '/tmp'
		data_dir = os.path.expanduser( data_dir )
		data_file = os.path.join( data_dir, 'analytics-sqlite.db' )
		dburi = "sqlite:///%s" % data_file
		
	logger.info( "Creating database at '%s'", dburi )	
	return AnalyticsDB( dburi, twophase, autocommit )

