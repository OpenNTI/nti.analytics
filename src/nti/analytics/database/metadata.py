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

from sqlalchemy.schema import Index
from sqlalchemy.schema import Sequence

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr

Base = declarative_base()

# This user_id should be the dataserver's intid value for this user.
class Users(Base):
	__tablename__ = 'Users'
	user_id = Column('user_id', Integer, Sequence('user_id_seq'), primary_key=True, index=True )
	user_ds_id = Column('user_ds_id', Integer, nullable=False, unique=True, index=True)
	
# TODO timezone?
class Sessions(Base):
	__tablename__ = 'Sessions'
	session_id = Column('session_id', Integer, primary_key=True)
	user_id = Column('user_id', Integer, ForeignKey("Users.user_id"), nullable=False )
	ip_addr = Column('ip_addr', String(64))	
	platform = Column('platform', String(64))
	version = Column('version', String(64))
	start_time = Column('start_time', DateTime)
	end_time = Column('end_time', DateTime)


class BaseTableMixin(object):

	# For migrating data, we may not have sessions (or timestamps); thus this is optional.
	# Does the same apply to users?  Perhaps we don't have a 'creator' stored.
	@declared_attr
	def session_id(cls):
		return Column('session_id', Integer, ForeignKey("Sessions.session_id"), nullable=True )
	
	@declared_attr
	def user_id(cls):
		return Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, primary_key=True )
	
	timestamp = Column('timestamp', DateTime, nullable=True )

class BaseViewMixin(object):

	# For resource views, we need timestamp to be non-null for primary key purposes.
	@declared_attr
	def session_id(cls):
		return Column('session_id', Integer, ForeignKey("Sessions.session_id"), nullable=True )
	
	@declared_attr
	def user_id(cls):
		return Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, primary_key=True )
	
	timestamp = Column('timestamp', DateTime, primary_key=True )

# TODO Some of these objects do not exist in the ds, thus we'll need a sequence.  Hopefully
# we don't need any data from the ds when retrieving this data.  If so, we need it here or another
# way to look it up.

# This information needs to be obscured to protect privacy.	
class ChatsInitiated(Base,BaseTableMixin):
	__tablename__ = 'ChatsInitiated'
	chat_id = Column('chat_id', Integer, nullable=False, index=True, primary_key=True )		

# Note, we're not tracking when users leave chat rooms.
class ChatsJoined(Base,BaseTableMixin):
	__tablename__ = 'ChatsJoined'
	chat_id = Column('chat_id', Integer, ForeignKey("ChatsInitiated.chat_id"), nullable=False, index=True, primary_key=True )		
	
class DeletedMixin(object):
	deleted = Column('deleted', DateTime)	
	
class DynamicFriendsListsCreated(Base,BaseTableMixin,DeletedMixin):
	__tablename__ = 'DynamicFriendsListsCreated'
	dfl_id = Column('dfl_id', Integer, nullable=False, index=True, primary_key=True )		
	
class DynamicFriendsListMixin(object):	
	@declared_attr
	def dfl_id(cls):
		return Column('dfl_id', Integer, ForeignKey("DynamicFriendsListsCreated.dfl_id"), nullable=False, index=True, primary_key=True )

class FriendMixin(object):	
	@declared_attr
	def target_id(cls):
		return Column('target_id', Integer, ForeignKey("Users.user_id"), index=True, primary_key=True)	
	
class DynamicFriendsListsMemberAdded(Base,BaseTableMixin,DynamicFriendsListMixin,FriendMixin):
	__tablename__ = 'DynamicFriendsListsMemberAdded'	
	
class DynamicFriendsListsMemberRemoved(Base,BaseTableMixin,DynamicFriendsListMixin,FriendMixin):
	__tablename__ = 'DynamicFriendsListsMemberRemoved'		

class FriendsListsCreated(Base,BaseTableMixin,DeletedMixin):
	__tablename__ = 'FriendsListsCreated'
	friends_list_id = Column('friends_list_id', Integer, nullable=False, index=True, primary_key=True )	
	
class FriendsListMixin(object):	
	@declared_attr
	def friends_list_id(cls):
		return Column('friends_list_id', Integer, ForeignKey("FriendsListsCreated.friends_list_id"), nullable=False, index=True, primary_key=True )	
	
class FriendsListsMemberAdded(Base,BaseTableMixin,FriendsListMixin,FriendMixin):
	__tablename__ = 'FriendsListsMemberAdded'	
	
class FriendsListsMemberRemoved(Base,BaseTableMixin,FriendsListMixin,FriendMixin):
	__tablename__ = 'FriendsListsMemberRemoved'		
	
# Contact events should(?) only reference the user-specific friends list.		
class ContactsAdded(Base,BaseTableMixin,FriendMixin):
	__tablename__ = 'ContactsAdded'

class ContactsRemoved(Base,BaseTableMixin,FriendMixin):
	__tablename__ = 'ContactsRemoved'
	
class ThoughtMixin(BaseViewMixin):	
	
	@declared_attr
	def thought_id(cls):
		return Column('thought_id', Integer, ForeignKey("ThoughtsCreated.thought_id"), nullable=False, index=True, primary_key=True )
	
class ThoughtsCreated(Base,BaseTableMixin):
	__tablename__ = 'ThoughtsCreated'	
	thought_id = Column('thought_id', Integer, nullable=False, index=True, primary_key=True )
	
class ThoughtsViewed(Base,ThoughtMixin):
	__tablename__ = 'ThoughtsViewed'	

class CourseMixin(object):
	course_id = Column('course_id', String(64), nullable=False, index=True, primary_key=True)
	
	@declared_attr
	def __table_args__(cls):
		return (Index('ix_%s_user_course' % cls.__tablename__, 'user_id', 'course_id'),)

class ResourceMixin(CourseMixin,BaseViewMixin):
	resource_id = Column('resource_id', String(1048), nullable=False, primary_key=True)
	
class ResourceViewMixin(ResourceMixin):
	context_path = Column('context_path', String(1048), nullable=False)

# Time length in seconds
class TimeLengthMixin(object):
	time_length = Column('time_length', Integer)
	

# For meta-views into synthetic course info, we can special type the resource_id:
#	(about|instructors|tech_support)	
class CourseResourceViews(Base,ResourceViewMixin,TimeLengthMixin):
	__tablename__ = 'CourseResourceViews'	


# Would we query on these separate event types? Probably not.
# If so, we may break them out into separate tables.	
# TODO: Punt, should we have separate rows for start/end?
# TODO Define questions we want to answer before we define this table.
# TODO We need to define what timestamp is here (start of event, end of event?)
class VideoEvents(Base,ResourceViewMixin,TimeLengthMixin):
	__tablename__ = 'VideoEvents'
	video_event_type = Column('video_event_type', Enum( 'WATCH', 'SKIP' ), nullable=False )
	video_start_time = Column('video_start_time', DateTime, nullable=False )
	video_end_time = Column('video_end_time', DateTime, nullable=False )
	with_transcript = Column('with_transcript', Boolean, nullable=False )
	
class NoteMixin(ResourceMixin):
	
	@declared_attr
	def note_id(cls):	
		return Column('note_id', Integer, ForeignKey("NotesCreated.note_id"), nullable=False, index=True, primary_key=True )
	
class NotesCreated(Base,ResourceMixin,DeletedMixin):	
	__tablename__ = 'NotesCreated'
	note_id = Column('note_id', Integer, nullable=False, index=True, primary_key=True )
	sharing = Column('sharing', Enum( 'PUBLIC', 'COURSE', 'OTHER', 'UNKNOWN' ), nullable=False )

class NotesViewed(Base,NoteMixin):	
	__tablename__ = 'NotesViewed'

class HighlightsCreated(Base,ResourceMixin,DeletedMixin):
	__tablename__ = 'HighlightsCreated'
	highlight_id = Column('highlight_id', Integer, nullable=False, index=True, primary_key=True )

class ForumsCreated(Base,BaseTableMixin,CourseMixin,DeletedMixin):		
	__tablename__ = 'ForumsCreated'
	forum_id = Column('forum_id', Integer, primary_key=True, index=True)				

class ForumMixin(CourseMixin):
	@declared_attr
	def forum_id(cls):
		return Column('forum_id', Integer, ForeignKey("ForumsCreated.forum_id"), nullable=False, primary_key=True)
	
class DiscussionsCreated(Base,BaseTableMixin,ForumMixin,DeletedMixin):	
	__tablename__ = 'DiscussionsCreated'
	discussion_id = Column('discussion_id', Integer, primary_key=True ) 
	
class DiscussionMixin(ForumMixin):	
	@declared_attr
	def discussion_id(cls):
		return Column('discussion_id', Integer, ForeignKey("DiscussionsCreated.discussion_id"), nullable=False, primary_key=True)

class DiscussionsViewed(Base,BaseViewMixin,DiscussionMixin,TimeLengthMixin):
	__tablename__ = 'DiscussionsViewed'	

class CommentsMixin(BaseTableMixin,DeletedMixin):
	# comment_id should be the DS intid
	@declared_attr
	def comment_id(cls):
		return Column('comment_id', Integer, nullable=False, primary_key=True)
	
	# parent_id should point to a parent comment, top-level comments will have null parent_ids
	@declared_attr
	def parent_id(cls):
		return Column('parent_id', Integer)

class ForumCommentsCreated(Base,CommentsMixin,DiscussionMixin):
	__tablename__ = 'ForumCommentsCreated'		
	
class BlogCommentsCreated(Base,CommentsMixin,ThoughtMixin):
	__tablename__ = 'BlogCommentsCreated'	
	
class NoteCommentsCreated(Base,CommentsMixin,NoteMixin):
	__tablename__ = 'NoteCommentsCreated'			


class CourseCatalogViews(Base,BaseViewMixin,CourseMixin,TimeLengthMixin):	
	__tablename__ = 'CourseCatalogViews'
	
# TODO how will we populate this, at migration time based on client?	
# or perhaps statically at first.
class EnrollmentTypes(Base):
	__tablename__ = 'EnrollmentTypes'
	type_id = Column( 'type_id', Integer, Sequence( 'enrollment_type_seq' ), nullable=False, primary_key=True )
	type_name = Column( 'type_name', String(64), nullable=False, index=True, unique=True )
		
# Dropped is redundant, but it may be useful to grab all course enrollment information here.		
class CourseEnrollments(Base,BaseTableMixin,CourseMixin):
	__tablename__ = 'CourseEnrollments'
	type_id = Column( 'type_id', Integer, ForeignKey( 'EnrollmentTypes.type_id' ), nullable=False )
	dropped = Column( 'dropped', DateTime, nullable=True )
	
class CourseDrops(Base,BaseTableMixin,CourseMixin):	
	__tablename__ = 'CourseDrops'

class AssignmentMixin(BaseTableMixin,CourseMixin,TimeLengthMixin):
	assignment_id = Column('assignment_id', String(1048), nullable=False, index=True, primary_key=True )
		
class SelfAssessmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'SelfAssessmentsTaken'
	submission_id = Column('submission_id', Integer, Sequence( 'self_assess_submission_id_seq' ), primary_key=True, index=True )
		
# TODO Should feedback have its own event tracking? It's one of the few mutable fields if not.
class AssignmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'AssignmentsTaken'
	grade = Column('grade', String(256))
	feedback_count = Column('feedback_count', Integer)
	submission_id = Column('submission_id', Integer, Sequence( 'assignment_submission_id_seq' ), primary_key=True, index=True )


class SubmissionMixin(AssignmentMixin):
	@declared_attr
	def question_id(cls):
		return Column('question_id', Integer, nullable=False, primary_key=True)
	
	@declared_attr
	def question_part(cls):
		return Column('question_part', Integer, nullable=False, primary_key=True)
	
	@declared_attr
	def submission(cls):
		return Column('submission', String(1048), nullable=False) #(Freeform|MapEntry|Index|List)
	
	@declared_attr
	def is_correct(cls):
		return Column('is_correct', Boolean)
	
# TODO Can we rely on these parts/ids being integers?
# TODO What do we do if instructor corrects an answer for a question_part (syncing)?
class AssignmentDetails(Base,SubmissionMixin):	
	__tablename__ = 'AssignmentDetails'
	submission_id = Column('submission_id', Integer, ForeignKey("AssignmentsTaken.submission_id"), nullable=False, primary_key=True)

class SelfAssessmentDetails(Base,SubmissionMixin):	
	__tablename__ = 'SelfAssessmentDetails'
	submission_id = Column('submission_id', Integer, ForeignKey("SelfAssessmentsTaken.submission_id"), nullable=False, primary_key=True)




## TODO LIST
#	examine String limits
#		-Should we use TEXT instead of String?
#		-If we use ntiids, we should probably expand. 
#	constraints
# 	Timestamps TEXT here?
#	Forum/Discussion ids, intids or other?
class AnalyticsMetadata(object): 

	def __init__(self,engine):
		logger.info( "Initializing database" )	
		Base.metadata.create_all(engine)
		
		