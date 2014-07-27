#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import json
from six import integer_types
from six import string_types

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError

import zope.intid
from zope import interface
from zope.sqlalchemy import ZopeTransactionExtension

from nti.dataserver.users.entity import Entity

from nti.app.products.gradebook.interfaces import IGrade

from nti.assessment.interfaces import IQAssessedQuestionSet
from nti.assessment.interfaces import IQUploadedFile
from nti.assessment.interfaces import IQModeledContentResponse

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
from .metadata import BlogsCreated
from .metadata import BlogsViewed
from .metadata import CourseResourceViews
from .metadata import VideoEvents
from .metadata import NotesCreated
from .metadata import NotesViewed
from .metadata import HighlightsCreated
from .metadata import ForumsCreated
from .metadata import TopicsCreated
from .metadata import TopicsViewed
from .metadata import ForumCommentsCreated
from .metadata import BlogCommentsCreated
from .metadata import CourseCatalogViews
from .metadata import EnrollmentTypes
from .metadata import CourseEnrollments
from .metadata import CourseDrops
from .metadata import AssignmentsTaken
from .metadata import AssignmentDetails
from .metadata import AssignmentGrades
from .metadata import AssignmentDetailGrades
from .metadata import AssignmentFeedback
from .metadata import SelfAssessmentsTaken
from .metadata import SelfAssessmentDetails

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import IDLookup
from nti.analytics.common import get_creator

def _get_duration( submission ):
	"""
	For a submission, retrieves how long it took to submit the object, in integer seconds.
	'-1' is returned if unknown.
	"""
	time_length = getattr( submission, 'CreatorRecordedEffortDuration', -1 )
	time_length = time_length or -1
	return int( time_length )

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

	# Note: we could also do private if not shared at all
	# or perhaps we want to store who we're sharing to.
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

	def create_user(self, user):
		# TODO Should we validate we have IUsers here, do we want to exclude other entities?
		uid = self.idlookup.get_id_for_user( user )
		if not uid:
			# FIXME Nothing we can do, not sure how we got here
			logger.exception( 'User has no user_id and cannot be inserted (uid=%s) (user=%s)', uid, user )
			return
		user = Users( user_ds_id=uid )
		# We'd like to use 'merge' here, but we cannot (in sqlite) if our primary key
		# is a sequence.
		self.session.add( user )
		try:
			self.session.flush()
			logger.info( 'Created user (user_id=%s) (user_ds_id=%s)', user.user_id, uid )
		except IntegrityError:
			# TODO if we have a race condition, we'll need to fetch the current user entry.
			logger.debug( 'User (%s) (db_id=%s) already exists on attempted insert', uid, user.user_id )
		return user

	def _get_or_create_user(self, user):
		# TODO Do we have to worry about race conditions?
		uid = self.idlookup.get_id_for_user( user )
		found_user = self.session.query(Users).filter( Users.user_ds_id == uid ).first()
		return found_user or self.create_user( uid )

	def create_session(self, user, session_id, timestamp, ip_address, platform, version):
		user = self._get_or_create_user( user )
		uid = user.user_id
		timestamp = timestamp_type( timestamp )

		new_session = Sessions( user_id=uid,
								session_id=session_id,
								start_time=timestamp,
								ip_addr=ip_address,
								platform=platform,
								version=version )
		self.session.add( new_session )

	def end_session(self, session_id, timestamp):
		timestamp = timestamp_type( timestamp )
		nti_session = self.session.query(Sessions).filter( Sessions.session_id == session_id ).first()
		if nti_session:
			nti_session.end_time = timestamp
		else:
			# This could happen during the initial startup phase, be forgiving.
			logger.debug( 'Session ending but no record found in Sessions table (sid=%s)', session_id )

	def create_chat_initiated(self, user, nti_session, chat):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		cid = self.idlookup.get_id_for_chat( chat )

		timestamp = get_created_timestamp( chat )

		new_object = ChatsInitiated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										chat_id=cid )
		self.session.add( new_object )

	def chat_joined(self, user, nti_session, timestamp, chat):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		cid = self.idlookup.get_id_for_chat( chat )
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
		sid = self.idlookup.get_id_for_session( nti_session )
		dfl_id = self.idlookup.get_id_for_dfl( dynamic_friends_list )
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
		if user is None:
			uid = None
		else:
			user = self._get_or_create_user( user )
			uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		dfl_id = self.idlookup.get_id_for_dfl( dynamic_friends_list )
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
		sid = self.idlookup.get_id_for_session( nti_session )
		dfl_id = self.idlookup.get_id_for_dfl( dynamic_friends_list )
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
		sid = self.idlookup.get_id_for_session( nti_session )
		friends_list_id = self.idlookup.get_id_for_friends_list( friends_list )
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

	def _delete_friend_list_member( self, friends_list_id, target_id ):
		friend = self.session.query(FriendsListsMemberAdded).filter( 	FriendsListsMemberAdded.friends_list_id==friends_list_id,
																		FriendsListsMemberAdded.target_id==target_id ).first()
		self.session.delete( friend )


	def _get_friends_list_members( self, friends_list_id ):
		results = self.session.query(FriendsListsMemberAdded).filter(
									FriendsListsMemberAdded.friends_list_id == friends_list_id ).all()
		return results

	def _get_contacts( self, uid ):
		results = self.session.query(ContactsAdded).filter(
									ContactsAdded.user_id == uid ).all()
		return results

	def update_contacts( self, user, nti_session, timestamp, friends_list ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		timestamp = timestamp_type( timestamp )

		members = self._get_contacts( uid )
		# This works because contacts are friends_list, and both
		# 'member' sets have 'target_id' columns we key off of.
		members_to_add, members_to_remove \
			= self._find_members( friends_list, members )

		for new_member in members_to_add:
			new_object = ContactsAdded( user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										target_id=new_member )

			self.session.add( new_object )
		for old_member in members_to_remove:
			new_object = ContactsRemoved( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											target_id=old_member )
			self.session.add( new_object )
			self._delete_contact_added( uid, old_member )

		return len( members_to_add ) - len( members_to_remove )

	def update_friends_list( self, user, nti_session, timestamp, friends_list ):
		friends_list_id = self.idlookup.get_id_for_friends_list( friends_list )
		members = self._get_friends_list_members( friends_list_id )
		members_to_add, members_to_remove \
			= self._find_members( friends_list, members )

		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		timestamp = timestamp_type( timestamp )

		for new_member in members_to_add:
			new_object = FriendsListsMemberAdded( 	user_id=uid,
													session_id=sid,
													timestamp=timestamp,
													friends_list_id=friends_list_id,
													target_id=new_member )
			self.session.add( new_object )
		for old_member in members_to_remove:
			new_object = FriendsListsMemberRemoved( user_id=uid,
													session_id=sid,
													timestamp=timestamp,
													friends_list_id=friends_list_id,
													target_id=old_member )
			self.session.add( new_object )
			self._delete_friend_list_member( friends_list_id, old_member )

		return len( members_to_add ) - len( members_to_remove )

	def _find_members( self, friends_list, members ):
		""" For a friends_list, return a tuple of members to add/remove. """
		members = set( [ x.target_id for x in members if x ] )
		new_members = set( [ self._get_or_create_user( x ).user_id for x in friends_list if x] )

		members_to_add = new_members - members
		members_to_remove = members - new_members

		return ( members_to_add, members_to_remove )

	def _delete_contact_added( self, user_id, target_id ):
		contact = self.session.query(ContactsAdded).filter(
											ContactsAdded.user_id == user_id,
											ContactsAdded.target_id == target_id ).first()
		self.session.delete( contact )

	def create_blog( self, user, nti_session, blog_entry ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		blog_id = self.idlookup.get_id_for_blog( blog_entry )

		timestamp = get_created_timestamp( blog_entry )

		new_object = BlogsCreated( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									blog_id=blog_id )
		self.session.add( new_object )

	def delete_blog( self, timestamp, blog_id ):
		blog = self.session.query(BlogsCreated).filter(
										BlogsCreated.blog_id == blog_id ).one()
		blog.deleted = timestamp

		self.session.query( BlogCommentsCreated ).filter(
							BlogCommentsCreated.blog_id == blog_id ).update(
										{ BlogCommentsCreated.deleted : timestamp } )
		self.session.flush()

	def create_blog_view(self, user, nti_session, timestamp, blog_entry):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		blog_id = self.idlookup.get_id_for_blog( blog_entry )
		timestamp = timestamp_type( timestamp )

		new_object = BlogsViewed( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									blog_id=blog_id )
		self.session.add( new_object )


	def create_course_resource_view(self, user, nti_session, timestamp, course, context_path, resource, time_length):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		rid = self.idlookup.get_id_for_resource( resource )
		course_id = self.idlookup.get_id_for_course( course )
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
							video_resource,
							time_length,
							video_event_type,
							video_start_time,
							video_end_time,
							with_transcript ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		vid = self.idlookup.get_id_for_resource( video_resource )
		course_id = self.idlookup.get_id_for_course( course )
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
		sid = self.idlookup.get_id_for_session( nti_session )
		rid = self.idlookup.get_id_for_resource( note.containerId )
		nid = self.idlookup.get_id_for_note( note )
		course_id = self.idlookup.get_id_for_course( course )
		timestamp = get_created_timestamp( note )
		sharing = _get_sharing_enum( note, course )

		pid = None
		parent_note = getattr( note, 'inReplyTo', None )
		if parent_note is not None:
			pid = self.idlookup.get_id_for_note( parent_note )

		new_object = NotesCreated( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									note_id=nid,
									resource_id=rid,
									parent_id=pid,
									sharing=sharing )
		self.session.add( new_object )

	def delete_note(self, timestamp, note_id):
		timestamp = timestamp_type( timestamp )
		note = self.session.query(NotesCreated).filter(
								NotesCreated.note_id == note_id ).one()
		note.deleted=timestamp
		self.session.flush()

	def create_note_view(self, user, nti_session, timestamp, course, note):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		rid = self.idlookup.get_id_for_resource( note.containerId )
		nid = self.idlookup.get_id_for_note( note )
		course_id = self.idlookup.get_id_for_course( course )
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
		sid = self.idlookup.get_id_for_session( nti_session )
		rid = self.idlookup.get_id_for_resource( highlight.containerId )
		hid = self.idlookup.get_id_for_highlight( highlight )
		course_id = self.idlookup.get_id_for_course( course )

		timestamp = get_created_timestamp( highlight )

		new_object = HighlightsCreated( user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										highlight_id=hid,
										resource_id=rid)
		self.session.add( new_object )

	def delete_highlight(self, timestamp, highlight_id):
		timestamp = timestamp_type( timestamp )
		highlight = self.session.query(HighlightsCreated).filter(
									HighlightsCreated.highlight_id == highlight_id ).one()
		highlight.deleted=timestamp
		self.session.flush()

	def create_forum(self, user, nti_session, course, forum):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		fid = self.idlookup.get_id_for_forum( forum )
		course_id = self.idlookup.get_id_for_course( course )

		timestamp = get_created_timestamp( forum )

		new_object = ForumsCreated( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									forum_id=fid )
		self.session.add( new_object )

	def delete_forum(self, timestamp, forum_id):
		timestamp = timestamp_type( timestamp )
		db_forum = self.session.query(ForumsCreated).filter( ForumsCreated.forum_id==forum_id ).one()
		db_forum.deleted=timestamp

		# Get our topics and comments
		self.session.query( TopicsCreated ).filter(
							TopicsCreated.forum_id == forum_id ).update( { TopicsCreated.deleted : timestamp } )
		self.session.query( ForumCommentsCreated ).filter(
							ForumCommentsCreated.forum_id == forum_id ).update(
								{ ForumCommentsCreated.deleted : timestamp } )
		self.session.flush()

	def create_topic(self, user, nti_session, course, topic):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		fid = self.idlookup.get_id_for_forum( topic.__parent__ )
		did = self.idlookup.get_id_for_topic( topic )
		course_id = self.idlookup.get_id_for_course( course )

		timestamp = get_created_timestamp( topic )

		new_object = TopicsCreated( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											topic_id=did )
		self.session.add( new_object )

	def delete_topic(self, timestamp, topic_id):
		timestamp = timestamp_type( timestamp )
		db_topic = self.session.query(TopicsCreated).filter( TopicsCreated.topic_id == topic_id ).one()
		db_topic.deleted = timestamp

		self.session.query( ForumCommentsCreated ).filter(
							ForumCommentsCreated.topic_id == topic_id ).update(
												{ ForumCommentsCreated.deleted : timestamp } )
		self.session.flush()

	def create_topic_view(self, user, nti_session, timestamp, course, topic, time_length):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		fid = self.idlookup.get_id_for_forum( topic.__parent__ )
		did = self.idlookup.get_id_for_topic( topic )
		course_id = self.idlookup.get_id_for_course( course )
		timestamp = timestamp_type( timestamp )

		new_object = TopicsViewed( user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										topic_id=did,
										time_length=time_length )
		self.session.add( new_object )

	def create_forum_comment(self, user, nti_session, course, topic, comment):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		forum = topic.__parent__
		fid = self.idlookup.get_id_for_forum(forum)
		did = self.idlookup.get_id_for_topic(topic)
		cid = self.idlookup.get_id_for_comment(comment)
		course_id = self.idlookup.get_id_for_course( course )
		pid = None
		timestamp = get_created_timestamp( comment )

		parent_comment = getattr( comment, 'inReplyTo', None )
		if parent_comment is not None:
			pid = self.idlookup.get_id_for_comment( parent_comment )

		new_object = ForumCommentsCreated( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											course_id=course_id,
											forum_id=fid,
											topic_id=did,
											parent_id=pid,
											comment_id=cid )
		self.session.add( new_object )

	def delete_forum_comment(self, timestamp, comment_id):
		timestamp = timestamp_type( timestamp )
		comment = self.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id==comment_id ).one()
		comment.deleted=timestamp
		self.session.flush()

	def create_blog_comment(self, user, nti_session, blog, comment ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		bid = self.idlookup.get_id_for_blog( blog )
		cid = self.idlookup.get_id_for_comment( comment )
		pid = None

		timestamp = get_created_timestamp( comment )
		parent_comment = getattr( comment, 'inReplyTo', None )
		if parent_comment is not None:
			pid = self.idlookup.get_id_for_comment( parent_comment )

		new_object = BlogCommentsCreated( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											blog_id=bid,
											parent_id=pid,
											comment_id=cid )
		self.session.add( new_object )

	def delete_blog_comment(self, timestamp, comment_id):
		timestamp = timestamp_type( timestamp )
		comment = self.session.query(BlogCommentsCreated).filter(
							BlogCommentsCreated.comment_id == comment_id ).one()
		comment.deleted=timestamp
		self.session.flush()

	def create_course_catalog_view(self, user, nti_session, timestamp, course, time_length):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		course_id = self.idlookup.get_id_for_course( course )
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
		sid = self.idlookup.get_id_for_session( nti_session )
		course_id = self.idlookup.get_id_for_course( course )
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
		sid = self.idlookup.get_id_for_session( nti_session )
		course_id = self.idlookup.get_id_for_course( course )
		timestamp = timestamp_type( timestamp )

		new_object = CourseDrops( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id )
		self.session.add( new_object )

		enrollment = self.session.query(CourseEnrollments).filter( 	CourseEnrollments.user_id == uid,
																CourseEnrollments.course_id == course_id ).first()
		enrollment.dropped = timestamp

	def _get_response(self, part):
		if IQUploadedFile.providedBy( part ):
			part = '<FILE_UPLOADED>'
		elif IQModeledContentResponse.providedBy( part ):
			part = ''.join( part.value )

		result = ''
		try:
			result = json.dumps( part )
		except TypeError:
			logger.exception( 'Submission response is not serializable (type=%s)', type( part ) )

		return result

	def create_self_assessment_taken(self, user, nti_session, timestamp, course, submission ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		course_id = self.idlookup.get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		submission_id = self.idlookup.get_id_for_submission( submission )
		self_assessment_id = submission.questionSetId
		# We likely will not have a grader.
		grader = self._get_grader_id( submission )
		# TODO As a QAssessedQuestionSet. we will not have a duration.
		# I don't believe the submission was saved; so we cannot get it back.
		# We'd have to transfer it during adaptation perhaps.
		time_length = _get_duration( submission )

		new_object = SelfAssessmentsTaken( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											course_id=course_id,
											assignment_id=self_assessment_id,
											submission_id=submission_id,
											time_length=time_length )
		self.session.add( new_object )

		for assessed_question in submission.questions:
			question_id = assessed_question.questionId

			for idx, part in enumerate( assessed_question.parts ):
				grade = part.assessedValue
				# TODO How do we do this?
				is_correct = grade == 1
				response = self._get_response( part.submittedResponse )
				grade_details = SelfAssessmentDetails( user_id=uid,
														session_id=sid,
														timestamp=timestamp,
														submission_id=submission_id,
														question_id=question_id,
														question_part_id=idx,
														is_correct=is_correct,
														grade=grade,
														grader=grader,
														submission=response,
														time_length=time_length )
				self.session.add( grade_details )

	def _get_grader_id( self, submission ):
		"""
		Returns a grader id for the submission if one exists (otherwise None).
		Currently, we have a one-to-one mapping between submission and grader.  That
		would need to change for things like peer grading.
		"""
		grader = None
		graded_submission = IGrade( submission, None )
		# If None, we're pending right?
		if graded_submission is not None:
			grader = get_creator( graded_submission )
			if grader is not None:
				grader = self._get_or_create_user( grader )
				grader = grader.user_id
		return grader

	def create_assignment_taken(self, user, nti_session, timestamp, course, submission ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		course_id = self.idlookup.get_id_for_course( course )
		timestamp = timestamp_type( timestamp )
		submission_id = self.idlookup.get_id_for_submission( submission )
		assignment_id = submission.assignmentId
		submission_obj = submission.Submission
		time_length = _get_duration( submission_obj )

		new_object = AssignmentsTaken( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										assignment_id=assignment_id,
										submission_id=submission_id,
										time_length=time_length )
		self.session.add( new_object )

		# Submission Parts
		for set_submission in submission_obj.parts:
			for question_submission in set_submission.questions:
				# Questions don't have ds_intids, just use ntiid.
				question_id = question_submission.questionId
				# We'd like this by part, but will accept by question for now.
				time_length = _get_duration( question_submission )

				for idx, part in enumerate( question_submission.parts ):
					# Serialize our response
					response = self._get_response( part )
					parts = AssignmentDetails( 	user_id=uid,
												session_id=sid,
												timestamp=timestamp,
												submission_id=submission_id,
												question_id=question_id,
												question_part_id=idx,
												submission=response,
												time_length=time_length )
					self.session.add( parts )

		# Grade
		graded_submission = IGrade( submission, None )
		# If None, we're pending right?
		if graded_submission is not None:
			grade = graded_submission.grade
			grader = self._get_grader_id( submission )

			graded = AssignmentGrades( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										submission_id=submission_id,
										grade=grade,
										grader=grader )
			self.session.add( graded )

			# Submission Part Grades
			for maybe_assessed in submission.pendingAssessment.parts:
				if not IQAssessedQuestionSet.providedBy(maybe_assessed):
					# We're not auto-graded
					continue
				for assessed_question in maybe_assessed.questions:
					question_id = assessed_question.questionId

					for idx, part in enumerate( assessed_question.parts ):
						grade = part.assessedValue
						# TODO How do we do this?
						is_correct = grade == 1
						grade_details = AssignmentDetailGrades( user_id=uid,
																session_id=sid,
																timestamp=timestamp,
																submission_id=submission_id,
																question_id=question_id,
																question_part_id=idx,
																is_correct=is_correct,
																grade=grade,
																grader=grader )
						self.session.add( grade_details )

	def grade_submission(self, user, nti_session, timestamp, grader, graded_val, submission ):
		grader = self._get_or_create_user( grader )
		grader_id  = grader.user_id
		submission_id = self.idlookup.get_id_for_submission( submission )
		grade_entry = self._get_grade_entry( submission_id )
		timestamp = timestamp_type( timestamp )

		if grade_entry:
			# Update
			# If we wanted, we could just append every 'set_grade' action.
			grade_entry.grade = graded_val
			grade_entry.timestamp = timestamp
			grade_entry.grader = grader_id
		else:
			# New grade
			user = self._get_or_create_user( user )
			uid = user.user_id
			sid = self.idlookup.get_id_for_session( nti_session )

			new_object = AssignmentGrades( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											submission_id=submission_id,
											grade=graded_val,
											grader=grader_id )

			self.session.add( new_object )

	def _get_grade_entry( self, submission_id ):
		# Currently, one assignment means one grade (and one grader).  If that changes, we'll
		# need to change this (at least)
		grade_entry = self.session.query(AssignmentGrades).filter(
													AssignmentGrades.submission_id==submission_id ).first()
		return grade_entry

	def _get_grade_id( self, submission_id ):
		grade_entry = self._get_grade_entry( submission_id )
		return grade_entry.grade_id

	def create_submission_feedback( self, user, nti_session, timestamp, submission, feedback ):
		user = self._get_or_create_user( user )
		uid = user.user_id
		sid = self.idlookup.get_id_for_session( nti_session )
		timestamp = timestamp_type( timestamp )
		feedback_id = self.idlookup.get_id_for_feedback( feedback )
		feedback_length = sum( len( x ) for x in feedback.body )

		submission_id = self.idlookup.get_id_for_submission( submission )
		# TODO Do we need to handle any of these being None?
		# That's an error condition, right?
		grade_id = self._get_grade_id( submission_id )

		new_object = AssignmentFeedback( user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										submission_id=submission_id,
										feedback_id=feedback_id,
										feedback_length=feedback_length,
										grade_id=grade_id )
		self.session.add( new_object )

	def delete_feedback( self, timestamp, feedback_id ):
		timestamp = timestamp_type( timestamp )
		feedback = self.session.query(AssignmentFeedback).filter(
								AssignmentFeedback.feedback_id == feedback_id ).one()
		feedback.deleted=timestamp
		self.session.flush()

	# StudentParticipationReport
	def get_forum_comments_for_user(self, user, course):
		user = self._get_or_create_user( user )
		uid = user.user_id
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.user_id == uid,
																ForumCommentsCreated.course_id == course_id,
																ForumCommentsCreated.deleted == None ).all()
		return results

	def get_topics_created_for_user(self, user, course):
		user = self._get_or_create_user( user )
		uid = user.user_id
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(TopicsCreated).filter( TopicsCreated.user_id == uid,
															TopicsCreated.course_id == course_id,
															TopicsCreated.deleted == None  ).all()
		return results

	def get_self_assessments_for_user(self, user, course):
		user = self._get_or_create_user( user )
		uid = user.user_id
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(SelfAssessmentsTaken).filter( 	SelfAssessmentsTaken.user_id == uid,
																	SelfAssessmentsTaken.course_id == course_id ).all()
		return results

	def get_assignments_for_user(self, user, course):
		user = self._get_or_create_user( user )
		uid = user.user_id
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(AssignmentsTaken).filter( 	AssignmentsTaken.user_id == uid,
																AssignmentsTaken.course_id == course_id ).all()
		return results

	#TopicReport
	def get_comments_for_topic(self, topic ):
		topic_id = self.idlookup.get_id_for_topic( topic )
		results = self.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.topic_id == topic_id ).all()
		return results


	#ForumReport
	def get_forum_comments(self, forum):
		forum_id = self.idlookup.get_id_for_forum( forum )
		results = self.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.forum_id == forum_id,
																	ForumCommentsCreated.deleted == None  ).all()
		return results

	def get_topics_created_for_forum(self, forum):
		forum_id = self.idlookup.get_id_for_forum( forum )
		results = self.session.query(TopicsCreated).filter( TopicsCreated.forum_id == forum_id,
																TopicsCreated.deleted == None  ).all()
		return results


	#CourseReport
	def get_forum_comments_for_course(self, course):
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.course_id == course_id,
																	ForumCommentsCreated.deleted == None  ).all()
		return results

	def get_topics_created_for_course(self, course):
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(TopicsCreated).filter( 	TopicsCreated.course_id == course_id,
																	TopicsCreated.deleted == None  ).all()
		return results

	def get_self_assessments_for_course(self, course):
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(SelfAssessmentsTaken).filter( SelfAssessmentsTaken.course_id == course_id ).all()
		return results

	def get_assignments_for_course(self, course):
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(AssignmentsTaken).filter( AssignmentsTaken.course_id == course_id ).all()
		return results

	def get_notes_created_for_course(self, course):
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(NotesCreated).filter( 	NotesCreated.course_id == course_id,
															NotesCreated.deleted == None  ).all()
		return results

	def get_highlights_created_for_course(self, course):
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(HighlightsCreated).filter( HighlightsCreated.course_id == course_id,
																HighlightsCreated.deleted == None  ).all()
		return results


	#AssignmentReport
	def get_assignment_details_for_course(self, course):
		course_id = self.idlookup.get_id_for_course( course )
		results = self.session.query(AssignmentDetails).\
							join(AssignmentsTaken).\
							filter( AssignmentsTaken.course_id == course_id ).all()
		return results

