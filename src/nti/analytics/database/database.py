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
import six

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .metadata import AnalyticsMetadata
from .interfaces import IAnalyticsDB

from nti.dataserver.users import interfaces as user_interfaces

from zope import interface
from zope import component
import zope.intid

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

from nti.utils.property import Lazy

class IDLookup(object):
	
	def __init__( self ):
		self.intids = component.getUtility(zope.intid.IIntIds)
		
	def _get_id_for_object( self, obj ):
		return self.intids.getId( obj )
	
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

	@Lazy
	def idlookup(self):
		return IDLookup()

	def get_session(self):
		Session = sessionmaker(bind=self.engine)
		return Session()
	
	def _get_id_for_user(self, user):
		# We may already have an integer id, use it.
		if isinstance( user, six.integer_types ):
			return user
		return self.idlookup._get_id_for_object( user )
	
	def _get_id_for_session(self, nti_session):
		return self.idlookup._get_id_for_object( nti_session )
	
	# FIXME we define discussions and notes has having string ids,
	# but we give back the intid here. Decide.
	
	def _get_id_for_forum(self, forum):
		return self.idlookup._get_id_for_object( forum )
	
	def _get_id_for_discussion(self, discussion):
		return self.idlookup._get_id_for_object( discussion )
	
	def _get_id_for_note(self, note):
		return self.idlookup._get_id_for_object( note )
	
	def _get_id_for_highlight(self, highlight):
		return self.idlookup._get_id_for_object( highlight )
	
	def _get_id_for_resource(self, resource):
		""" Resource could be a video or content piece. """
		return self.idlookup._get_id_for_object( resource )
	
	def _get_id_for_thought(self, thought):
		return self.idlookup._get_id_for_object( thought )
	
	def _get_id_for_chat(self, chat):
		return self.idlookup._get_id_for_object( chat )
	
	def create_user(self, session, user):
		uid = self._get_id_for_user( user )
		user = Users( user_ds_id=uid )
		session.add( user )
		session.flush()
		return user
		
	def _get_or_create_user(self, session, user):	
		# TODO We use this throughout in other transactions, is the negative case not indicative of 
		# data incorrectness? Should we barf? Same with enrollment_type
		# TODO Do we have to worry about race conditions?
		uid = self._get_id_for_user( user )
		found_user = session.query(Users).filter( Users.user_ds_id == uid ).one()
		return found_user or self.create_user( session, uid )
		
	def create_session(self, session, user, nti_session, ip_address, platform, version):
		# TODO nti_session does not exist yet, probably
		# ISessionService from nti.dataserver?
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_session = Sessions( user_id=uid, 
								session_id=sid, 
								timestamp=nti_session.timestamp, 
								ip_addr=ip_address, 
								platform=platform, 
								version=version )
		session.add( new_session )		
		
	def create_chat_initated(self, session, user, nti_session, timestamp, chat ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		cid = self._get_id_for_chat( chat )
		
		new_object = ChatsInitiated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										chat_id=chat )
		session.add( new_object )		
		
	def create_chat_joined(self, session, user, nti_session, timestamp, chat):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		cid = self._get_id_for_chat( chat )
		
		new_object = ChatsJoined( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									chat_id=cid )
		session.add( new_object )	
		
	def create_group(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = GroupsCreated( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp )
		session.add( new_object )	
		
	def remove_group(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = GroupsRemoved( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp )
		session.add( new_object )	
		
	def create_distribution_list(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = DistributionListsCreated( 	user_id=uid, 
												session_id=sid, 
												timestamp=timestamp )
		session.add( new_object )	
		
	def create_contact_added(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = ContactsAdded( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp )
		session.add( new_object )	
		
	def create_contact_removed(self, session, user, nti_session, timestamp):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = ContactsRemoved( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp )
		session.add( new_object )	
		
	def create_thought(self, session, user, nti_session, timestamp, thought):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		tid = self._get_id_for_thought( thought )
		
		new_object = ThoughtsCreated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										thought_id=tid )
		session.add( new_object )	
		
	def create_thought_view(self, session, user, nti_session, timestamp, thought):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		tid = self._get_id_for_thought( thought )
		
		new_object = ThoughtsViewed( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										thought_id=tid )
		session.add( new_object )				
			
			
	def create_course_resource_view(self, session, user, nti_session, timestamp, course_id, context_path, resource, time_length):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( resource )
		
		new_object = CourseResourceViews( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											context_path=context_path,
											resource_id=rid,
											time_length=time_length )
		session.add( new_object )	
		
	# TODO resource_id lookup?
	def create_video_event(	self, session, user, 
							nti_session, timestamp, 
							course_id, context_path, 
							resource_id, time_length,
							video_event_type,
							video_start_time,
							video_end_time,
							video_resource,
							with_transcript ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		vid = self._get_id_for_resource( video_resource )
		
		new_object = VideoEvents(	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									context_path=context_path,
									resource_id=vid,
									time_length=time_length,
									video_event_type=video_event_type,
									video_start_time=video_start_time,
									video_end_time=video_end_time,
									with_transcript=with_transcript )
		session.add( new_object )	
			
	def create_note(self, session, user, nti_session, timestamp, course_id, resource, note, sharing):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( resource )
		nid = self._get_id_for_note(note)
		
		new_object = NotesCreated( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									note_id=nid,
									resource_id=rid,
									sharing=sharing )
		session.add( new_object )
		
	def delete_note(self, session, timestamp, note):	
		nid = self._get_id_for_note(note)
		note = session.query(NotesCreated).filter( note_id=nid ).one()
		note.deleted=timestamp
		session.flush()
		
	def create_note_view(self, session, user, nti_session, timestamp, course_id, resource, note):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( resource )
		nid = self._get_id_for_note( note )
		
		new_object = NotesViewed( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									resource_id=rid,
									note_id=nid )
		session.add( new_object )
	
	def create_highlight(self, session, user, nti_session, timestamp, course_id, highlight, resource):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( resource )
		hid = self._get_id_for_highlight(highlight)
		
		new_object = HighlightsCreated( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										highlight_id=hid,
										resource_id=rid)
		session.add( new_object )
		
	def delete_highlight(self, session, timestamp, highlight):	
		hid = self._get_id_for_highlight(highlight)
		highlight = session.query(HighlightsCreated).filter( highlight_id=hid ).one()
		highlight.deleted=timestamp
		session.flush()	
	
	def create_forum(self, session, user, nti_session, timestamp, course_id, forum):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum(forum)
		
		new_object = ForumsCreated( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									forum_id=fid )
		session.add( new_object )
		
	def delete_forum(self, session, timestamp, forum):	
		fid = self._get_id_for_forum(forum)
		forum = session.query(ForumsCreated).filter( forum_id=fid ).one()
		forum.deleted=timestamp
		session.flush()		
		
	def create_discussion(self, session, user, nti_session, timestamp, course_id, forum, discussion):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum(forum)
		did = self._get_id_for_discussion(discussion)
		
		new_object = DiscussionsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											discussion_id=did )
		session.add( new_object )	
		
	def delete_forum(self, session, timestamp, discussion):	
		did = self._get_id_for_discussion(discussion)
		discussion = session.query(DiscussionsCreated).filter( discussion_id=did ).one()
		discussion.deleted=timestamp
		session.flush()			
		
	def create_discussion_view(self, session, user, nti_session, timestamp, course_id, forum, discussion, time_length):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum(forum)
		did = self._get_id_for_discussion(discussion)
		
		new_object = DiscussionsViewed( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										discussion_id=did,
										time_length=time_length )
		session.add( new_object )	
		
	def create_forum_comment_created(self, session, user, nti_session, timestamp, course_id, forum, discussion, parent_id, comment):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum(forum)
		did = self._get_id_for_discussion(discussion)
		cid = self._get_id_for_comment(comment)
		
		new_object = ForumCommentsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											discussion_id=did,
											parent_id=parent_id,
											comment_id=cid )
		session.add( new_object )	
		
	def delete_forum_comment(self, session, timestamp, comment):	
		cid = self._get_id_for_comment(comment)
		comment = session.query(ForumCommentsCreated).filter( comment_id=cid ).one()
		comment.deleted=timestamp
		session.flush()		
		
	def create_blog_comment_created(self, session, user, nti_session, timestamp, course_id, forum, discussion, parent_id, comment):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum(forum)
		did = self._get_id_for_discussion(discussion)
		cid = self._get_id_for_comment(comment)
		
		new_object = BlogCommentsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											discussion_id=did,
											parent_id=parent_id,
											comment_id=cid )
		session.add( new_object )	
		
	def delete_blog_comment(self, session, timestamp, comment):	
		cid = self._get_id_for_comment(comment)
		comment = session.query(BlogCommentsCreated).filter( comment_id=cid ).one()
		comment.deleted=timestamp
		session.flush()			
		
	def create_note_comment_created(self, session, user, nti_session, timestamp, course_id, forum, discussion, parent_id, comment):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum(forum)
		did = self._get_id_for_discussion(discussion)
		cid = self._get_id_for_comment(comment)
		
		new_object = NoteCommentsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											discussion_id=did,
											parent_id=parent_id,
											comment_id=cid )
		session.add( new_object )	
		
	def delete_note_comment(self, session, timestamp, comment):	
		cid = self._get_id_for_comment(comment)
		comment = session.query(NoteCommentsCreated).filter( comment_id=cid ).one()
		comment.deleted=timestamp
		session.flush()		
		
	def create_course_catalog_view(self, session, user, nti_session, timestamp, course_id, time_length):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = CourseCatalogView( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										time_length=time_length )
		session.add( new_object )						
	
	def create_enrollment_type(self, session, name):
		enrollment_type = EnrollmentTypes( type_name=type_name )
		session.add( enrollment_type )
		session.flush()
		return enrollment_type
	
	def _get_enrollment_id(self, session, name):
		enrollment_type = session.query(EnrollmentTypes).filter( EnrollmentTypes.type_name == name ).one()
		return enrollment_type or create_enrollment_type(self,session,name)
	
	def create_course_enrollment(self, session, user, nti_session, timestamp, course_id, enrollment_type_name):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		type_id = self._get_enrollment_id( session, enrollment_type_name )
		
		new_object = CourseEnrollments( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										type_id=type_id )
		session.add( new_object )
		
	def create_course_drop(self, session, user, nti_session, timestamp, course_id):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = CourseDrops( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id )
		session.add( new_object )	
		
	def create_self_assessment_taken(self, session, user, nti_session, timestamp, course_id, self_assessment_id, time_length, questions, submission ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_object = SelfAssessmentsTaken( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											assignment_id=self_assessment_id,
											time_length=time_length )
		session.add( new_object )		
	
		# We should have questions, parts, submissions, and is_correct
		# TODO What objects will we have here?
	
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

