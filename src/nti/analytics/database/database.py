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
from six import integer_types
from six import string_types

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from zope import interface
from zope import component
import zope.intid

from pyramid.location import lineage

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.users import interfaces as user_interfaces

from nti.dataserver.users.entity import Entity

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost

from nti.utils.property import Lazy

from .interfaces import IAnalyticsDB

from .metadata import AnalyticsMetadata
from .metadata import Users
from .metadata import Sessions
from .metadata import ChatsInitiated
from .metadata import ChatsJoined
from .metadata import DynamicFriendsListsCreated
from .metadata import DynamicFriendsListsRemoved
from .metadata import DynamicFriendsListsMemberAdded
from .metadata import DynamicFriendsListsMemberRemoved
from .metadata import FriendsListsCreated
from .metadata import FriendsListsRemoved
from .metadata import FriendsListsMemberAdded
from .metadata import FriendsListsMemberRemoved
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

class IDLookup(object):
	
	def __init__( self ):
		self.intids = component.getUtility(zope.intid.IIntIds)
		
	def _get_id_for_object( self, obj ):
		result = getattr( obj, '_ds_intid', None )
		return result or self.intids.getId( obj )
	
def _get_course_from_lineage( obj ):	
	# TODO Verify this works
	result = None
	for location in lineage( obj ):
		if ICourseInstance.providedBy( location ):
			result = ICourseInstance( location )
			break
	return result
	
def _get_sharing_enum(note):		
	# Logic duped in coursewarereports.views.admin_views
	course = _get_course_from_lineage( note )
	if not course:
		# TODO What do we want to do here?
		logger.warn( 'Could not retrieve course from object (%s)', note )
		return 'UNKNOWN'
	
	scopes = course.LegacyScopes
	public = scopes['public']
	course_only = scopes['restricted']

	public_object = Entity.get_entity( public )
	course_only_object = Entity.get_entity( course_only )
	
	result = 'OTHER'
	
	if public_object in note.sharingTargets:
		result = 'PUBLIC'
	elif course_only_object in note.sharingTargets:
		result = 'COURSE'
		
	return result	
	
# We should only have a few different types of operations here:
# - Insertions
# - Deleted objects will modify 'deleted' column with timestamp
# - Modify feedback column (?)
# - Modify Session end timestamp
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
		if isinstance( user, integer_types ):
			return user
		return self.idlookup._get_id_for_object( user )
	
	def _get_id_for_session(self, nti_session):
		return self.idlookup._get_id_for_object( nti_session )
	
	def _get_id_for_comment(self, comment):
		return self.idlookup._get_id_for_object( comment )
	
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
		if isinstance( resource, string_types ):
			result = resource
		else:
			result = getattr( resource, 'ntiid', None )
		return result
	
	def _get_id_for_thought(self, thought):
		return self.idlookup._get_id_for_object( thought )
	
	def _get_id_for_chat(self, chat):
		return self.idlookup._get_id_for_object( chat )
	
	def _get_id_for_dfl(self, dfl):
		return self.idlookup._get_id_for_object( dfl )
	
	def _get_id_for_friends_list(self, friends_list):
		return self.idlookup._get_id_for_object( friends_list )
	
	def _get_timestamp(self, obj):
		result = getattr( obj, 'createdTime', None )
		return result or datetime.utcnow()
	
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
		# TODO Allow for idempotency?
		# TODO Some of these objects will not have creators/users during migration.
		uid = self._get_id_for_user( user )
		found_user = session.query(Users).filter( Users.user_ds_id == uid ).first()
		return found_user or self.create_user( session, uid )
		
	def create_session(self, session, user, nti_session, timestamp, ip_address, platform, version):
		# TODO nti_session does not exist yet, probably
		# ISessionService from nti.dataserver?
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_session = Sessions( user_id=uid, 
								session_id=sid, 
								start_time=timestamp, 
								ip_addr=ip_address, 
								platform=platform, 
								version=version )
		session.add( new_session )		
		
	def end_session(self, session, nti_session, timestamp):
		sid = self._get_id_for_session( nti_session )
		nti_session = session.query(Sessions).filter( Sessions.session_id == sid ).first()
		nti_session.end_time = timestamp
		session.flush()
		
	#nti.chatserver.meeting._Meeting	
	def create_chat_initiated(self, session, user, nti_session, chat ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		cid = self._get_id_for_chat( chat )
		
		timestamp = self._get_timestamp( chat )
		
		new_object = ChatsInitiated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										chat_id=cid )
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
		
	# DFLs	
	def create_dynamic_friends_list(self, session, user, nti_session, timestamp, dynamic_friends_list ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		dfl_id = self._get_id_for_dfl( dynamic_friends_list )
		
		new_object = DynamicFriendsListsCreated( 	user_id=uid, 
													session_id=sid, 
													timestamp=timestamp,
													dfl_id=dfl_id )
		session.add( new_object )	
		
	def remove_dynamic_friends_list(self, session, user, nti_session, timestamp, dynamic_friends_list ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		dfl_id = self._get_id_for_dfl( dynamic_friends_list )
		
		new_object = DynamicFriendsListsRemoved( 	user_id=uid, 
													session_id=sid, 
													timestamp=timestamp,
													dfl_id=dfl_id )
		session.add( new_object )		
		
	def create_dynamic_friends_member(self, session, user, nti_session, timestamp, dynamic_friends_list, new_friend ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		dfl_id = self._get_id_for_dfl( dynamic_friends_list )
		target = self._get_or_create_user( session, new_friend )
		target_id = target.user_id
		
		new_object = DynamicFriendsListsMemberAdded( 	user_id=uid, 
														session_id=sid, 
														timestamp=timestamp,
														dfl_id=dfl_id,
														target_id=target_id )
		session.add( new_object )		
		
	def _delete_dynamic_friend_list_member( self, session, dfl_id, target_id ):
		friend = session.query(DynamicFriendsListsMemberAdded).filter( 
											DynamicFriendsListsMemberAdded.dfl_id==dfl_id, 
											DynamicFriendsListsMemberAdded.target_id==target_id ).first()
		session.delete( friend )	
		
	def remove_dynamic_friends_member(self, session, user, nti_session, timestamp, dynamic_friends_list, new_friend ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		dfl_id = self._get_id_for_dfl( dynamic_friends_list )
		target = self._get_or_create_user( session, new_friend )
		target_id = target.user_id
		
		new_object = DynamicFriendsListsMemberRemoved( 	user_id=uid, 
														session_id=sid, 
														timestamp=timestamp,
														dfl_id=dfl_id,
														target_id=target_id )
		session.add( new_object )	
		self._delete_dynamic_friend_list_member( session, dfl_id, target_id )	
		
	# FLs	
	def create_friends_list(self, session, user, nti_session, timestamp, friends_list):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		friends_list_id = self._get_id_for_friends_list( friends_list )
		
		new_object = FriendsListsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											friends_list_id=friends_list_id )
		session.add( new_object )	
		
	def remove_friends_list(self, session, user, nti_session, timestamp, friends_list ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		friends_list_id = self._get_id_for_friends_list( friends_list )
		
		new_object = FriendsListsRemoved( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											friends_list_id=friends_list_id )
		session.add( new_object )		
		
	def create_friends_list_member(self, session, user, nti_session, timestamp, friends_list, new_friend ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		friends_list_id = self._get_id_for_friends_list( friends_list )
		target = self._get_or_create_user( session, new_friend )
		target_id = target.user_id
		
		new_object = FriendsListsMemberAdded( 	user_id=uid, 
												session_id=sid, 
												timestamp=timestamp,
												friends_list_id=friends_list_id,
												target_id=target_id )
		session.add( new_object )		
		
	def _delete_friend_list_member( self, session, friends_list_id, target_id ):
		friend = session.query(FriendsListsMemberAdded).filter( FriendsListsMemberAdded.friends_list_id==friends_list_id, 
																FriendsListsMemberAdded.target_id==target_id ).first()
		session.delete( friend )	
		
	def remove_friends_list_member(self, session, user, nti_session, timestamp, friends_list, new_friend ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		friends_list_id = self._get_id_for_friends_list( friends_list )
		target = self._get_or_create_user( session, new_friend )
		target_id = target.user_id
		
		new_object = FriendsListsMemberRemoved( user_id=uid, 
												session_id=sid, 
												timestamp=timestamp,
												friends_list_id=friends_list_id,
												target_id=target_id )
		session.add( new_object )	
		self._delete_friend_list_member(session, friends_list_id, target_id)	
	
	# Magical FL	
	# See DefaultComputedContacts
	# During migration, we'll want to pull this from user objects and capture events 
	# during runtime.
	def create_contact_added( self, session, user, nti_session, timestamp, new_contact ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		target = self._get_or_create_user( session, new_contact )
		target_id = target.user_id
		
		new_object = ContactsAdded( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										target_id=target_id )
		session.add( new_object )	
	
	def _delete_contact_added( self, session, user_id, target_id ):
		contact = session.query(ContactsAdded).filter( 	ContactsAdded.user_id==user_id, 
														ContactsAdded.target_id==target_id ).first()
		session.delete( contact )
		
	def create_contact_removed( self, session, user, nti_session, timestamp, new_contact ):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		target = self._get_or_create_user( session, new_contact )
		target_id = target.user_id
		
		new_object = ContactsRemoved( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										target_id=target_id )
		session.add( new_object )	
		self._delete_contact_added( session, uid, target_id )
		
	def create_thought(self, session, user, nti_session, blog_entry):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		tid = self._get_id_for_thought( blog_entry )
		
		timestamp = self._get_timestamp( blog_entry )
		
		new_object = ThoughtsCreated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										thought_id=tid )
		session.add( new_object )	
		
	def create_thought_view(self, session, user, nti_session, timestamp, blog_entry):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		tid = self._get_id_for_thought( blog_entry )
		
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
		
	def create_video_event(	self, session, user, 
							nti_session, timestamp, 
							course_id, context_path, 
							time_length,
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
			
			
	def create_note(self, session, user, nti_session, course_id, note):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( note.__parent__ )
		nid = self._get_id_for_note( note )
		
		timestamp = self._get_timestamp( note )
		# TODO verify -> resource = note.__parent__?
		
		sharing = _get_sharing_enum(note)
		
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
		note = session.query(NotesCreated).filter( NotesCreated.note_id==nid ).one()
		note.deleted=timestamp
		session.flush()
		
	def create_note_view(self, session, user, nti_session, timestamp, course_id, note):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( note.__parent__ )
		nid = self._get_id_for_note( note )
		
		new_object = NotesViewed( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									resource_id=rid,
									note_id=nid )
		session.add( new_object )
	
	def create_highlight(self, session, user, nti_session, course_id, highlight):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( highlight.__parent__ )
		hid = self._get_id_for_highlight( highlight )
		
		timestamp = self._get_timestamp( highlight )
		
		new_object = HighlightsCreated( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										highlight_id=hid,
										resource_id=rid)
		session.add( new_object )
		
	def delete_highlight(self, session, timestamp, highlight):	
		hid = self._get_id_for_highlight(highlight)
		highlight = session.query(HighlightsCreated).filter( HighlightsCreated.highlight_id==hid ).one()
		highlight.deleted=timestamp
		session.flush()	
	
	#nti.dataserver.contenttypes.forums.forum.CommunityForum
	def create_forum(self, session, user, nti_session, course_id, forum):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum( forum )
		
		timestamp = self._get_timestamp( forum )
		
		new_object = ForumsCreated( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									forum_id=fid )
		session.add( new_object )
		
	def delete_forum(self, session, timestamp, forum):	
		fid = self._get_id_for_forum(forum)
		forum = session.query(ForumsCreated).filter( ForumsCreated.forum_id==fid ).one()
		forum.deleted=timestamp
		session.flush()		
		
	#nti.dataserver.contenttypes.forums.topic.CommunityHeadlineTopic	
	def create_discussion(self, session, user, nti_session, course_id, topic):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum( topic.__parent__ )
		did = self._get_id_for_discussion( topic )
		
		timestamp = self._get_timestamp( topic )
		
		new_object = DiscussionsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											discussion_id=did )
		session.add( new_object )	
		
	def delete_discussion(self, session, timestamp, topic ):	
		did = self._get_id_for_discussion( topic )
		topic = session.query(DiscussionsCreated).filter( DiscussionsCreated.discussion_id==did ).one()
		topic.deleted=timestamp
		session.flush()			
		
	def create_discussion_view(self, session, user, nti_session, timestamp, course_id, topic, time_length):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum( topic.__parent__ )
		did = self._get_id_for_discussion( topic )
		
		new_object = DiscussionsViewed( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										discussion_id=did,
										time_length=time_length )
		session.add( new_object )	
		
	def create_forum_comment_created(self, session, user, nti_session, timestamp, course_id, forum, discussion, comment):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum(forum)
		did = self._get_id_for_discussion(discussion)
		cid = self._get_id_for_comment(comment)
		pid = None
		
		if ICommentPost.providedBy( comment.__parent__ ):
			pid = self._get_id_for_comment( comment.__parent__ )
		
		new_object = ForumCommentsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											discussion_id=did,
											parent_id=pid,
											comment_id=cid )
		session.add( new_object )	
		
	def delete_forum_comment(self, session, timestamp, comment):	
		cid = self._get_id_for_comment(comment)
		comment = session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id==cid ).one()
		comment.deleted=timestamp
		session.flush()		
		
	def create_blog_comment_created(self, session, user, nti_session, timestamp, blog, comment):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		bid = self._get_id_for_thought(blog)
		cid = self._get_id_for_comment(comment)
		pid = None
		
		if ICommentPost.providedBy( comment.__parent__ ):
			pid = self._get_id_for_comment( comment.__parent__ )
		
		new_object = BlogCommentsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											thought_id=bid,
											parent_id=pid,
											comment_id=cid )
		session.add( new_object )	
		
	def delete_blog_comment(self, session, timestamp, comment):	
		cid = self._get_id_for_comment(comment)
		comment = session.query(BlogCommentsCreated).filter( BlogCommentsCreated.comment_id==cid ).one()
		comment.deleted=timestamp
		session.flush()			
		
	def create_note_comment_created(self, session, user, nti_session, timestamp, course_id, note, comment):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		nid = self._get_id_for_note(note)
		rid = self._get_id_for_resource( note.__parent__ )
		cid = self._get_id_for_comment(comment)
		pid = None
		
		if ICommentPost.providedBy( comment.__parent__ ):
			pid = self._get_id_for_comment( comment.__parent__ )
		
		new_object = NoteCommentsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											note_id=nid,
											resource_id=rid,
											parent_id=pid,
											comment_id=cid )
		session.add( new_object )	
		
	def delete_note_comment(self, session, timestamp, comment):	
		cid = self._get_id_for_comment(comment)
		comment = session.query(NoteCommentsCreated).filter( NoteCommentsCreated.comment_id==cid ).one()
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
	
	def create_enrollment_type(self, session, type_name):
		enrollment_type = EnrollmentTypes( type_name=type_name )
		session.add( enrollment_type )
		session.flush()
		return enrollment_type
	
	def _get_enrollment_type_id(self, session, type_name):
		enrollment_type = session.query(EnrollmentTypes).filter( EnrollmentTypes.type_name == type_name ).one()
		return enrollment_type or self.create_enrollment_type( session, type_name )
	
	def create_course_enrollment(self, session, user, nti_session, timestamp, course_id, enrollment_type_name):
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		type_id = self._get_enrollment_type_id( session, enrollment_type_name )
		
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
		user = self._get_or_create_user( session, user )
		uid = user.user_id
		results = session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.user_id == uid, 
																ForumCommentsCreated.course_id == course_id, 
																ForumCommentsCreated.deleted == None ).all()
		return results
	
	def get_discussions_created_for_user(self, session, user, course_id):
		user = self._get_or_create_user( session, user )
		uid = user.user_id			
		results = session.query(DiscussionsCreated).filter( DiscussionsCreated.user_id == uid, 
															DiscussionsCreated.course_id == course_id, 
															DiscussionsCreated.deleted == None  ).all()
		return results
	
	def get_self_assessments_for_user(self, session, user, course_id):	
		user = self._get_or_create_user( session, user )
		uid = user.user_id		
		results = session.query(SelfAssessmentsTaken).filter( 	SelfAssessmentsTaken.user_id == uid, 
																SelfAssessmentsTaken.course_id == course_id ).all()
		return results
	
	def get_assignments_for_user(self, session, user, course_id):	
		user = self._get_or_create_user( session, user )
		uid = user.user_id	
		results = session.query(AssignmentsTaken).filter( 	AssignmentsTaken.user_id == uid, 
															AssignmentsTaken.course_id == course_id ).all()
		return results
	
	#TopicReport
	def get_comments_for_discussion(self, session, discussion ):
		discussion_id = self._get_id_for_discussion( discussion )
		results = session.query(ForumCommentsCreated).filter( ForumCommentsCreated.discussion_id == discussion_id ).all()
		return results
	
	
	#ForumReport
	def get_forum_comments(self, session, forum):
		forum_id = self._get_id_for_forum( forum )
		results = session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.forum_id == forum_id, 
																ForumCommentsCreated.deleted == None  ).all()
		return results
	
	def get_discussions_created_for_forum(self, session, forum):	
		forum_id = self._get_id_for_forum( forum )	
		results = session.query(DiscussionsCreated).filter( DiscussionsCreated.forum_id == forum_id, 
															DiscussionsCreated.deleted == None  ).all()
		return results
	
	
	#CourseReport
	def get_forum_comments_for_course(self, session, course_id):
		results = session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.course_id == course_id, 
																ForumCommentsCreated.deleted == None  ).all()
		return results
	
	def get_discussions_created_for_course(self, session, course_id):		
		results = session.query(DiscussionsCreated).filter( DiscussionsCreated.course_id == course_id, 
															DiscussionsCreated.deleted == None  ).all()
		return results
	
	def get_self_assessments_for_course(self, session, course_id):		
		results = session.query(SelfAssessmentsTaken).filter( SelfAssessmentsTaken.course_id == course_id ).all()
		return results
	
	def get_assignments_for_course(self, session, course_id):		
		results = session.query(AssignmentsTaken).filter( AssignmentsTaken.course_id == course_id ).all()
		return results
	
	def get_notes_created_for_course(self, session, course_id):		
		results = session.query(NotesCreated).filter( 	NotesCreated.course_id == course_id, 
														NotesCreated.deleted == None  ).all()
		return results
	
	def get_highlights_created_for_course(self, session, course_id):		
		results = session.query(HighlightsCreated).filter( 	HighlightsCreated.course_id == course_id, 
															HighlightsCreated.deleted == None  ).all()
		return results
	
	
	#AssignmentReport
	def get_assignment_details_for_course(self, session, course_id):		
		results = session.query(AssignmentDetails).filter( AssignmentDetails.course_id == course_id ).all()
		return results

