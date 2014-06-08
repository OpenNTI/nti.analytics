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

from .metadata import AnalyticsMetadata
from .interfaces import IAnalyticsDB

from nti.dataserver.users import interfaces as user_interfaces

from zope import interface
from zope import component

from .metadata import Users
from .metadata import Sessions
from .metadata import ChatsInitiated
from .metadata import ChatsJoined
from .metadata import GroupsCreated
from .metadata import GroupsRemoved
from .metadata import DistributionListsCreated
from .metadata import ContactsAdded
from .metadata import ContactsRemoved
from .metadata import ThoughtsCreated
from .metadata import ThoughtsViewed
from .metadata import CourseResourceViews
from .metadata import VideoEvents
from .metadata import NotesCreated
from .metadata import NotesViewed
from .metadata import HighlightsCreated
from .metadata import ForumsCreated
from .metadata import DiscussionsCreated
from .metadata import DiscussionsViewed
from .metadata import ForumCommentsCreated
from .metadata import BlogCommentsCreated
from .metadata import NoteCommentsCreated
from .metadata import CourseCatalogViews
from .metadata import EnrollmentTypes
from .metadata import CourseEnrollments
from .metadata import CourseDrops
from .metadata import AssignmentsTaken
from .metadata import AssignmentDetails
from .metadata import SelfAssessmentsTaken
from .metadata import SelfAssessmentDetails

from zope.intid import IIntIds

class IDLookup(object):
	
	def __init__( self ):
		intids = component.getUtility(IIntIds)	
		
	def _get_id_for_object( self, obj ):
	 return intids.getId( obj )
	
	def _get_id_for_session( self, session ):
		 return _get_id_for_object( session )	

# We should only have a few different types of operations here:
# - Insertions
# - Deleted objects will modify 'deleted' column with timestamp
# - Modify feedback column (?)
# - Session end timestamp
# - Reads
@interface.implementer(IAnalyticsDB)
class AnalyticsDB(object):
	
	def __init__( self, dburi=None, twophase=False, autocommit=False, defaultSQLite=False ):
		self.dburi = dburi
		self.twophase = twophase
		self.autocommit = autocommit
		
		if defaultSQLite and not dburi:
			data_dir = os.getenv( 'DATASERVER_DATA_DIR' ) or '/tmp'
			data_dir = os.path.expanduser( data_dir )
			data_file = os.path.join( data_dir, 'analytics-sqlite.db' )
			self.dburi = "sqlite:///%s" % data_file
			
		logger.info( "Creating database at '%s'", self.dburi )
		self.engine = create_engine(self.dburi, echo=False )
		self.metadata = AnalyticsMetadata( self.engine )
		self.idlookup = IDLookup()

	def get_session(self):
		Session = sessionmaker(bind=self.engine)
		return Session()
	
	
	def create_user(self, session, user):
		uid = self.idlookup._get_id_for_object( user )
		user = Users( user_ds_id=uid )
		session.add( user )
		session.flush()
		return user
		
	def _get_or_create_user(self, session, user):	
		# TODO We use this throughout in other transactions, is the negative case not indicative of 
		# data incorrectness? Should we barf?
		uid = self.idlookup._get_id_for_object( user )
		found_user = session.query(Users).filter( Users.user_ds_id == uid ).one()
		return found_user or self.create_user( session, uid )
		
	def create_session(self, session, user, nti_session, ip_address, platform, version):
		# TODO nti_session does not exist yet, probably
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_session = Sessions( user_id=uid, 
								session_id=sid, 
								timestamp=nti_session.timestamp, 
								ip_addr=ip_address, 
								platform=platform, 
								version=version )
		session.add( new_session )		
		
	def create_chat_initated(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = ChatsInitiated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp )
		session.add( new_object )		
		
	def create_chat_joined(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = _get_id_for_session( nti_session )
		
		new_object = ChatsJoined( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp )
		session.add( new_object )	
		
	def create_group(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = GroupsCreated( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp )
		session.add( new_object )	
		
	def remove_group(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = GroupsRemoved( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp )
		session.add( new_object )	
		
	def create_distribution_list(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = DistributionListsCreated( 	user_id=uid, 
												session_id=sid, 
												timestamp=timestamp )
		session.add( new_object )	
		
	def create_contact_added(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = ContactsAdded( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp )
		session.add( new_object )	
		
	def create_contact_removed(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = ContactsRemoved( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp )
		session.add( new_object )	
		
	def create_thought(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = ThoughtsCreated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp )
		session.add( new_object )	
		
	def create_thought_view(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = ThoughtsViewed( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp )
		session.add( new_object )				
			
			
	def create_course_resource_view(self, session, user, nti_session, timestamp, course_id, context_path, resource_id, time_length):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = CourseResourceViews( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											context_path=context_path,
											resource_id=resource_id,
											time_length=time_length )
		session.add( new_object )	
		
	def create_video_event(	self, session, user, 
							nti_session, timestamp, 
							course_id, context_path, 
							resource_id, time_length,
							video_event_type,
							video_start_time,
							video_end_time,
							with_transcript ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = VideoEvents(	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									context_path=context_path,
									resource_id=resource_id,
									time_length=time_length,
									video_event_type=video_event_type,
									video_start_time=video_start_time,
									video_end_time=video_end_time,
									with_transcript=with_transcript )
		session.add( new_object )	
			
	def create_note(self, session, user, nti_session, timestamp, course_id, resource_id, sharing):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = NotesCreated( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									resource_id=resource_id,
									sharing=sharing )
		session.add( new_object )
		
	# TODO Deleted notes
	# TODO Deleted forums
	# TODO Deleted highlights
	# TODO Deleted dsicussions	
	
	# TODO handle resource, forum, and discussion ids
	
	def create_note_view(self, session, user, nti_session, timestamp, course_id, resource_id, sharing):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = NotesViewed( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									resource_id=resource_id,
									sharing=sharing )
		session.add( new_object )
	
	def create_highlight(self, session, user, nti_session, timestamp, course_id, resource_id):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = HighlightsCreated( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										resource_id=resource_id)
		session.add( new_object )
	
	def create_forum(self, session, user, nti_session, timestamp, course_id, forum_id):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = ForumsCreated( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									forum_id=forum_id )
		session.add( new_object )
		
	def create_discussion(self, session, user, nti_session, timestamp, course_id, forum_id, discussion_id):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self.idlookup._get_id_for_session( nti_session )
		
		new_object = DiscussionsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=forum_id,
											discussion_id=discussion_id )
		session.add( new_object )	
	
	# StudentParticipationReport	
	def get_forum_comments_for_user(self, session, user, course_id):		
		results = session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.user_id == user.intid, 
																ForumCommentsCreated.course_id==course_id, 
																ForumCommentsCreated.deleted==None ).all()
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
		results = session.query(CommentsCreated).filter( CommentsCreated.discussion_id==discussion_id ).all()
		return results
	
	
	#ForumReport
	def get_forum_comments(self, session, forum_id):
		results = session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.forum_id==forum_id, 
																ForumCommentsCreated.deleted==None  ).all()
		return results
	
	def get_discussions_created_for_forum(self, session, forum_id):		
		results = session.query(DiscussionsCreated).filter( forum_id=forum_id, deleted=None  ).all()
		return results
	
	
	#CourseReport
	def get_forum_comments_for_course(self, session, course_id):
		results = session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.course_id==course_id, 
																ForumCommentsCreated.deleted==None  ).all()
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

