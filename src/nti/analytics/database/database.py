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

from contextlib import contextmanager

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError

import zope.intid
from zope import interface
from zope.sqlalchemy import ZopeTransactionExtension

from pyramid.location import lineage

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
from .metadata import DynamicFriendsListsMemberAdded
from .metadata import DynamicFriendsListsMemberRemoved
from .metadata import FriendsListsCreated
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

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import IDLookup

def _get_sharing_enum( note, course ):		
	# Logic duped in coursewarereports.views.admin_views
	if 		not course \
		or 	isinstance( course, ( integer_types, string_types ) ):
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
# - Modify self.session end timestamp
# - Reads
@interface.implementer(IAnalyticsDB)
class AnalyticsDB(object):
	
	pool_size = 30
	max_overflow = 10
	pool_recycle = 300
	
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
		self.metadata = AnalyticsMetadata( self.engine )

	@Lazy
	def engine(self):
		try:
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
		if self.autocommit:
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

	@Lazy
	def idlookup(self):
		return IDLookup()

	def _get_id_for_user(self, user):
		if not user:
			return None
		# We may already have an integer id, use it.
		if isinstance( user, integer_types ):
			return user
		return self.idlookup.get_id_for_object( user )
	
	def _get_id_for_session(self, nti_session):
		if not nti_session:
			return None
		return self.idlookup.get_id_for_object( nti_session )
	
	def _get_id_for_course( self, course ):
		# ID needs to be unique by semester...
		if isinstance( course, ( integer_types, string_types ) ):
			return course
		return self.idlookup.get_id_for_object( course )
	
	def _get_id_for_comment(self, comment):
		return self.idlookup.get_id_for_object( comment )
	
	def _get_id_for_forum(self, forum):
		return self.idlookup.get_id_for_object( forum )
	
	def _get_id_for_discussion(self, discussion):
		return self.idlookup.get_id_for_object( discussion )
	
	def _get_id_for_note(self, note):
		return self.idlookup.get_id_for_object( note )
	
	def _get_id_for_highlight(self, highlight):
		return self.idlookup.get_id_for_object( highlight )
	
	def _get_id_for_resource(self, resource):
		""" Resource could be a video or content piece. """
		if isinstance( resource, string_types ):
			result = resource
		else:
			result = getattr( resource, 'ntiid', None )
		return result
	
	def _get_id_for_thought(self, thought):
		return self.idlookup.get_id_for_object( thought )
	
	def _get_id_for_chat(self, chat):
		return self.idlookup.get_id_for_object( chat )
	
	def _get_id_for_dfl(self, dfl):
		return self.idlookup.get_id_for_object( dfl )
	
	def _get_id_for_friends_list(self, friends_list):
		return self.idlookup.get_id_for_object( friends_list )
	
	def create_user(self, user):
		uid = self._get_id_for_user( user )
		user = Users( user_ds_id=uid )
		# We'd like to use 'merge' here, but we cannot (in sqlite) if our primary key
		# is a sequence.
		self.session.add( user )
		try:
			self.session.flush()
		except IntegrityError:
			# TODO if we have a race condition, we'll need to fetch the current user entry.
			logger.debug( 'User (%s) (db_id=%s) already exists on attempted insert', uid, user.user_id )
		return user
		
	def _get_or_create_user(self, user):	
		# We use this throughout in other transactions, is the negative case not indicative of 
		# data incorrectness? Should we barf? Same with enrollment_type
		# TODO Do we have to worry about race conditions?
		# TODO Some of these objects will not have creators/users during migration.
		uid = self._get_id_for_user( user )
		found_user = self.session.query(Users).filter( Users.user_ds_id == uid ).first()
		return found_user or self.create_user( uid )
		
	def create_session(self, user, nti_session, timestamp, ip_address, platform, version):
		# FIXME nti_session does not exist yet, probably
		# ISessionService from nti.dataserver?
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		
		new_session = Sessions( user_id=uid, 
								session_id=sid, 
								start_time=timestamp, 
								ip_addr=ip_address, 
								platform=platform, 
								version=version )
		self.session.add( new_session )		
		
	def end_session(self, nti_session, timestamp):
		sid = self._get_id_for_session( nti_session )
		nti_session = self.session.query(Sessions).filter( Sessions.session_id == sid ).first()
		nti_session.end_time = timestamp
		
	#nti.chatserver.meeting._Meeting	
	def create_chat_initiated(self, user, nti_session, chat):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		cid = self._get_id_for_chat( chat )
		
		timestamp = get_created_timestamp( chat )
		
		new_object = ChatsInitiated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										chat_id=cid )
		self.session.add( new_object )		
		
	def chat_joined(self, user, nti_session, timestamp, chat):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		cid = self._get_id_for_chat( chat )
		timestamp = timestamp_type( timestamp )
		
		new_object = ChatsJoined( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									chat_id=cid )
		self.session.add( new_object )	
		try:
			self.session.flush()
		except IntegrityError:
			logger.debug( 'User (%s) already exists in chat (%s)', uid, chat )
		return user
		
	# DFLs	
	def create_dynamic_friends_list(self, user, nti_session, dynamic_friends_list):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		dfl_id = self._get_id_for_dfl( dynamic_friends_list )
		timestamp = get_created_timestamp( dynamic_friends_list )
		
		new_object = DynamicFriendsListsCreated( 	user_id=uid, 
													session_id=sid, 
													timestamp=timestamp,
													dfl_id=dfl_id )
		self.session.add( new_object )
		
	# Note: with this and friends_list, we're leaving members in their
	# (now deleted) groups.  This could be useful (or we can remove 
	# them at a later date).	
	def remove_dynamic_friends_list(self, timestamp, dfl_id):
		timestamp = timestamp_type( timestamp )	
		db_dfl = self.session.query(DynamicFriendsListsCreated).filter( DynamicFriendsListsCreated.dfl_id==dfl_id ).one()
		db_dfl.deleted=timestamp
		self.session.flush()
		
	def create_dynamic_friends_member(self, user, nti_session, timestamp, dynamic_friends_list, new_friend ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		dfl_id = self._get_id_for_dfl( dynamic_friends_list )
		target = self._get_or_create_user( new_friend )
		target_id = target.user_id
		timestamp = timestamp_type( timestamp )
		
		new_object = DynamicFriendsListsMemberAdded( 	user_id=uid, 
														session_id=sid, 
														timestamp=timestamp,
														dfl_id=dfl_id,
														target_id=target_id )
		self.session.add( new_object )		
		
	def _delete_dynamic_friend_list_member( self, dfl_id, target_id ):
		friend = self.session.query( DynamicFriendsListsMemberAdded ).filter( 
											DynamicFriendsListsMemberAdded.dfl_id==dfl_id, 
											DynamicFriendsListsMemberAdded.target_id==target_id ).first()
		self.session.delete( friend )	
		
	def remove_dynamic_friends_member(self, user, nti_session, timestamp, dynamic_friends_list, target ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		dfl_id = self._get_id_for_dfl( dynamic_friends_list )
		target = self._get_or_create_user( target )
		target_id = target.user_id
		timestamp = timestamp_type( timestamp )
		
		new_object = DynamicFriendsListsMemberRemoved( 	user_id=uid, 
														session_id=sid, 
														timestamp=timestamp,
														dfl_id=dfl_id,
														target_id=target_id )
		self.session.add( new_object )	
		self._delete_dynamic_friend_list_member( dfl_id, target_id )	
		
	# FLs	
	def create_friends_list(self, user, nti_session, timestamp, friends_list):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		friends_list_id = self._get_id_for_friends_list( friends_list )
		timestamp = timestamp_type( timestamp )
		
		new_object = FriendsListsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											friends_list_id=friends_list_id )
		self.session.add( new_object )	
		
	def remove_friends_list(self, timestamp, friends_list_id):
		timestamp = timestamp_type( timestamp )	
		db_friends_list = self.session.query(FriendsListsCreated).filter( FriendsListsCreated.friends_list_id==friends_list_id ).one()
		db_friends_list.deleted=timestamp
		self.session.flush()
		
	def create_friends_list_member(self, user, nti_session, timestamp, friends_list, new_friend ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		friends_list_id = self._get_id_for_friends_list( friends_list )
		target = self._get_or_create_user( new_friend )
		target_id = target.user_id
		timestamp = timestamp_type( timestamp )
		
		new_object = FriendsListsMemberAdded( 	user_id=uid, 
												session_id=sid, 
												timestamp=timestamp,
												friends_list_id=friends_list_id,
												target_id=target_id )
		self.session.add( new_object )		
		
	def _delete_friend_list_member( self, friends_list_id, target_id ):
		friend = self.session.query(FriendsListsMemberAdded).filter( 	FriendsListsMemberAdded.friends_list_id==friends_list_id, 
																		FriendsListsMemberAdded.target_id==target_id ).first()
		self.session.delete( friend )	
		
	def remove_friends_list_member(self, user, nti_session, timestamp, friends_list, new_friend ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		friends_list_id = self._get_id_for_friends_list( friends_list )
		target = self._get_or_create_user( new_friend )
		target_id = target.user_id
		timestamp = timestamp_type( timestamp )
		
		new_object = FriendsListsMemberRemoved( user_id=uid, 
												session_id=sid, 
												timestamp=timestamp,
												friends_list_id=friends_list_id,
												target_id=target_id )
		self.session.add( new_object )	
		self._delete_friend_list_member( friends_list_id, target_id )	
	
	# Magical FL	
	# See DefaultComputedContacts
	# During migration, we'll want to pull this from user objects and capture events 
	# during runtime.
	def create_contact_added( self, user, nti_session, timestamp, target ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		target = self._get_or_create_user( target )
		target_id = target.user_id
		timestamp = timestamp_type( timestamp )
		
		new_object = ContactsAdded( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										target_id=target_id )
		self.session.add( new_object )	
	
	def _delete_contact_added( self, user_id, target_id ):
		contact = self.session.query(ContactsAdded).filter( ContactsAdded.user_id==user_id, 
															ContactsAdded.target_id==target_id ).first()
		self.session.delete( contact )
		
	def contact_removed( self, user, nti_session, timestamp, target ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		target = self._get_or_create_user( target )
		target_id = target.user_id
		timestamp = timestamp_type( timestamp )
		
		new_object = ContactsRemoved( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										target_id=target_id )
		self.session.add( new_object )	
		self._delete_contact_added( uid, target_id )
		
	def create_blog( self, user, nti_session, blog_entry ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		tid = self._get_id_for_thought( blog_entry )
		
		timestamp = get_created_timestamp( blog_entry )
		
		new_object = ThoughtsCreated( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										thought_id=tid )
		self.session.add( new_object )	
		
	def create_blog_view(self, user, nti_session, timestamp, blog_entry):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		tid = self._get_id_for_thought( blog_entry )
		timestamp = timestamp_type( timestamp )
		
		new_object = ThoughtsViewed( 	user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										thought_id=tid )
		self.session.add( new_object )				
			
			
	def create_course_resource_view(self, user, nti_session, timestamp, course, context_path, resource, time_length):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( resource )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
		new_object = CourseResourceViews( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											context_path=context_path,
											resource_id=rid,
											time_length=time_length )
		self.session.add( new_object )	
		
	def create_video_event(	self, user, 
							nti_session, timestamp, 
							course, context_path, 
							time_length,
							video_event_type,
							video_start_time,
							video_end_time,
							video_resource,
							with_transcript ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		vid = self._get_id_for_resource( video_resource )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
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
		self.session.add( new_object )	
			
			
	def create_note(self, user, nti_session, course, note):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( note.containerId )
		nid = self._get_id_for_note( note )
		course_id = self._get_id_for_course( course )
		timestamp = get_created_timestamp( note )
		
		sharing = _get_sharing_enum( note, course )
		
		new_object = NotesCreated( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									note_id=nid,
									resource_id=rid,
									sharing=sharing )
		self.session.add( new_object )
		
	def delete_note(self, timestamp, note):
		timestamp = timestamp_type( timestamp )	
		nid = self._get_id_for_note(note)
		note = self.session.query(NotesCreated).filter( NotesCreated.note_id==nid ).one()
		note.deleted=timestamp
		self.session.flush()
		
	def create_note_view(self, user, nti_session, timestamp, course, note):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( note.containerId )
		nid = self._get_id_for_note( note )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
		new_object = NotesViewed( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									resource_id=rid,
									note_id=nid )
		self.session.add( new_object )
	
	def create_highlight(self, user, nti_session, course, highlight):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		rid = self._get_id_for_resource( highlight.containerId )
		hid = self._get_id_for_highlight( highlight )
		course_id = self._get_id_for_course( course )
		
		timestamp = get_created_timestamp( highlight )
		
		new_object = HighlightsCreated( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										highlight_id=hid,
										resource_id=rid)
		self.session.add( new_object )
		
	def delete_highlight(self, timestamp, highlight):	
		timestamp = timestamp_type( timestamp )
		hid = self._get_id_for_highlight(highlight)
		highlight = self.session.query(HighlightsCreated).filter( HighlightsCreated.highlight_id==hid ).one()
		highlight.deleted=timestamp
		self.session.flush()	
	
	#nti.dataserver.contenttypes.forums.forum.CommunityForum
	def create_forum(self, user, nti_session, course, forum):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum( forum )
		course_id = self._get_id_for_course( course )
		
		timestamp = get_created_timestamp( forum )
		
		new_object = ForumsCreated( user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id,
									forum_id=fid )
		self.session.add( new_object )
		
	def delete_forum(self, timestamp, forum):
		timestamp = timestamp_type( timestamp )	
		fid = self._get_id_for_forum(forum)
		db_forum = self.session.query(ForumsCreated).filter( ForumsCreated.forum_id==fid ).one()
		db_forum.deleted=timestamp

		for topic in forum.values():
			self.delete_discussion(timestamp, topic)
		self.session.flush()		
		
	#nti.dataserver.contenttypes.forums.topic.CommunityHeadlineTopic	
	def create_discussion(self, user, nti_session, course, topic):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum( topic.__parent__ )
		did = self._get_id_for_discussion( topic )
		course_id = self._get_id_for_course( course )
		
		timestamp = get_created_timestamp( topic )
		
		new_object = DiscussionsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											discussion_id=did )
		self.session.add( new_object )	
		
	def delete_discussion(self, timestamp, topic):	
		timestamp = timestamp_type( timestamp )
		did = self._get_id_for_discussion( topic )
		db_topic = self.session.query(DiscussionsCreated).filter( DiscussionsCreated.discussion_id==did ).one()
		db_topic.deleted=timestamp
		
		for comment in topic.values():
			self.delete_forum_comment(timestamp, comment)
		self.session.flush()			
		
	def create_discussion_view(self, user, nti_session, timestamp, course, topic, time_length):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		fid = self._get_id_for_forum( topic.__parent__ )
		did = self._get_id_for_discussion( topic )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
		new_object = DiscussionsViewed( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										discussion_id=did,
										time_length=time_length )
		self.session.add( new_object )	
		
	def create_forum_comment(self, user, nti_session, course, discussion, comment):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		forum = discussion.__parent__
		fid = self._get_id_for_forum(forum)
		did = self._get_id_for_discussion(discussion)
		cid = self._get_id_for_comment(comment)
		course_id = self._get_id_for_course( course )
		pid = None
		timestamp = get_created_timestamp( comment )
		
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
		self.session.add( new_object )	
		
	def delete_forum_comment(self, timestamp, comment):	
		timestamp = timestamp_type( timestamp )
		cid = self._get_id_for_comment(comment)
		comment = self.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id==cid ).one()
		comment.deleted=timestamp
		self.session.flush()		
		
	def create_blog_comment(self, user, nti_session, blog, comment ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		bid = self._get_id_for_thought( blog )
		cid = self._get_id_for_comment( comment )
		pid = None
		
		timestamp = get_created_timestamp( comment )
		
		if ICommentPost.providedBy( comment.__parent__ ):
			pid = self._get_id_for_comment( comment.__parent__ )
		
		new_object = BlogCommentsCreated( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											thought_id=bid,
											parent_id=pid,
											comment_id=cid )
		self.session.add( new_object )	
		
	def delete_blog_comment(self, timestamp, comment):	
		timestamp = timestamp_type( timestamp )
		cid = self._get_id_for_comment(comment)
		comment = self.session.query(BlogCommentsCreated).filter( BlogCommentsCreated.comment_id==cid ).one()
		comment.deleted=timestamp
		self.session.flush()			
		
	def create_note_comment(self, user, nti_session, course, note, comment):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		nid = self._get_id_for_note( note )
		rid = self._get_id_for_resource( note.__parent__ )
		cid = self._get_id_for_comment( comment )
		pid = None
		course_id = self._get_id_for_course( course )
		
		timestamp = get_created_timestamp( comment )
		
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
		self.session.add( new_object )	
		
	def delete_note_comment(self, timestamp, comment):
		timestamp = timestamp_type( timestamp )	
		cid = self._get_id_for_comment(comment)
		comment = self.session.query(NoteCommentsCreated).filter( NoteCommentsCreated.comment_id==cid ).one()
		comment.deleted=timestamp
		self.session.flush()		
		
	def create_course_catalog_view(self, user, nti_session, timestamp, course, time_length):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
		new_object = CourseCatalogViews( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											time_length=time_length )
		self.session.add( new_object )						
	
	def create_enrollment_type(self, type_name):
		enrollment_type = EnrollmentTypes( type_name=type_name )
		self.session.add( enrollment_type )
		self.session.flush()
		return enrollment_type
	
	def _get_enrollment_type_id(self, type_name):
		enrollment_type = self.session.query(EnrollmentTypes).filter( EnrollmentTypes.type_name == type_name ).first()
		return enrollment_type or self.create_enrollment_type( type_name )
	
	def create_course_enrollment(self, user, nti_session, timestamp, course, enrollment_type_name):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
		enrollment_type = self._get_enrollment_type_id( enrollment_type_name )
		type_id = enrollment_type.type_id
		
		new_object = CourseEnrollments( user_id=uid, 
										session_id=sid, 
										timestamp=timestamp,
										course_id=course_id,
										type_id=type_id )
		self.session.add( new_object )
		
	def create_course_drop(self, user, nti_session, timestamp, course):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
		new_object = CourseDrops( 	user_id=uid, 
									session_id=sid, 
									timestamp=timestamp,
									course_id=course_id )
		self.session.add( new_object )	
		
		enrollment = self.session.query(CourseEnrollments).filter( 	CourseEnrollments.user_id == uid,
																CourseEnrollments.course_id == course_id ).first()
		enrollment.dropped = timestamp
		
	def create_self_assessment_taken(self, user, nti_session, timestamp, course, self_assessment_id, time_length, questions, submission ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self._get_id_for_session( nti_session )
		course_id = self._get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		
		new_object = SelfAssessmentsTaken( 	user_id=uid, 
											session_id=sid, 
											timestamp=timestamp,
											course_id=course_id,
											assignment_id=self_assessment_id,
											time_length=time_length )
		self.session.add( new_object )		
	
		# We should have questions, parts, submissions, and is_correct
		# TODO What objects will we have here?
	
	# StudentParticipationReport	
	def get_forum_comments_for_user(self, user, course):	
		user = self._get_or_create_user( user )
		uid = user.user_id
		course_id = self._get_id_for_course( course )
		results = self.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.user_id == uid, 
																ForumCommentsCreated.course_id == course_id, 
																ForumCommentsCreated.deleted == None ).all()
		return results
	
	def get_discussions_created_for_user(self, user, course):
		user = self._get_or_create_user( user )
		uid = user.user_id			
		course_id = self._get_id_for_course( course )
		results = self.session.query(DiscussionsCreated).filter( DiscussionsCreated.user_id == uid, 
															DiscussionsCreated.course_id == course_id, 
															DiscussionsCreated.deleted == None  ).all()
		return results
	
	def get_self_assessments_for_user(self, user, course):	
		user = self._get_or_create_user( user )
		uid = user.user_id	
		course_id = self._get_id_for_course( course )	
		results = self.session.query(SelfAssessmentsTaken).filter( 	SelfAssessmentsTaken.user_id == uid, 
																	SelfAssessmentsTaken.course_id == course_id ).all()
		return results
	
	def get_assignments_for_user(self, user, course):	
		user = self._get_or_create_user( user )
		uid = user.user_id	
		course_id = self._get_id_for_course( course )
		results = self.session.query(AssignmentsTaken).filter( 	AssignmentsTaken.user_id == uid, 
																AssignmentsTaken.course_id == course_id ).all()
		return results
	
	#TopicReport
	def get_comments_for_discussion(self, discussion ):
		discussion_id = self._get_id_for_discussion( discussion )
		results = self.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.discussion_id == discussion_id ).all()
		return results
	
	
	#ForumReport
	def get_forum_comments(self, forum):
		forum_id = self._get_id_for_forum( forum )
		results = self.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.forum_id == forum_id, 
																	ForumCommentsCreated.deleted == None  ).all()
		return results
	
	def get_discussions_created_for_forum(self, forum):	
		forum_id = self._get_id_for_forum( forum )	
		results = self.session.query(DiscussionsCreated).filter( DiscussionsCreated.forum_id == forum_id, 
																DiscussionsCreated.deleted == None  ).all()
		return results
	
	
	#CourseReport
	def get_forum_comments_for_course(self, course):
		course_id = self._get_id_for_course( course )
		results = self.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.course_id == course_id, 
																	ForumCommentsCreated.deleted == None  ).all()
		return results
	
	def get_discussions_created_for_course(self, course):		
		course_id = self._get_id_for_course( course )
		results = self.session.query(DiscussionsCreated).filter( 	DiscussionsCreated.course_id == course_id, 
																	DiscussionsCreated.deleted == None  ).all()
		return results
	
	def get_self_assessments_for_course(self, course):		
		course_id = self._get_id_for_course( course )
		results = self.session.query(SelfAssessmentsTaken).filter( SelfAssessmentsTaken.course_id == course_id ).all()
		return results
	
	def get_assignments_for_course(self, course):	
		course_id = self._get_id_for_course( course )	
		results = self.session.query(AssignmentsTaken).filter( AssignmentsTaken.course_id == course_id ).all()
		return results
	
	def get_notes_created_for_course(self, course):	
		course_id = self._get_id_for_course( course )	
		results = self.session.query(NotesCreated).filter( 	NotesCreated.course_id == course_id, 
															NotesCreated.deleted == None  ).all()
		return results
	
	def get_highlights_created_for_course(self, course):	
		course_id = self._get_id_for_course( course )	
		results = self.session.query(HighlightsCreated).filter( HighlightsCreated.course_id == course_id, 
																HighlightsCreated.deleted == None  ).all()
		return results
	
	
	#AssignmentReport
	def get_assignment_details_for_course(self, course ):		
		course_id = self._get_id_for_course( course )
		results = self.session.query(AssignmentDetails).filter( AssignmentDetails.course_id == course_id ).all()
		return results

