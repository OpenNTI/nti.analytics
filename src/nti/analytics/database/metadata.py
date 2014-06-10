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
# TODO Do we need indexes here?	
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

	@declared_attr
	def session_id(cls):
		return Column('session_id', Integer, ForeignKey("Sessions.session_id"), primary_key=True)
	
	@declared_attr
	def user_id(cls):
		return Column('user_id', Integer, ForeignKey("Users.user_id"), primary_key=True, index=True)
	
	# We could default the timestamp to the current time, but we may have insertion lag.
	timestamp = Column('timestamp', DateTime, primary_key=True)


# TODO Some of these objects do not exist in the ds, thus we'll need a sequence.  Hopefully
# we don't need any data from the ds when retrieving this data.  If so, we need it here.

# This information needs to be obscured to protect privacy.	
class ChatsInitiated(Base,BaseTableMixin):
	__tablename__ = 'ChatsInitiated'
	chat_id = Column('chat_id', Integer, nullable=False, index=True )		

class ChatsJoined(Base,BaseTableMixin):
	__tablename__ = 'ChatsJoined'
	chat_id = Column('chat_id', Integer, ForeignKey("ChatsInitiated.chat_id"), nullable=False, index=True )		
	
class GroupsCreated(Base,BaseTableMixin):
	__tablename__ = 'GroupsCreated'
	
class GroupsRemoved(Base,BaseTableMixin):
	__tablename__ = 'GroupsRemoved'	
	
class DistributionListsCreated(Base,BaseTableMixin):
	__tablename__ = 'DistributionListsCreated'
	
class ContactsAdded(Base,BaseTableMixin):
	__tablename__ = 'ContactsAdded'

# Contact events should(?) only reference the user-specific friends list.	
class ContactsRemoved(Base,BaseTableMixin):
	__tablename__ = 'ContactsRemoved'
	
class ThoughtsCreated(Base,BaseTableMixin):
	__tablename__ = 'ThoughtsCreated'	
	thought_id = Column('thought_id', Integer, nullable=False, index=True )
	
class ThoughtsViewed(Base,BaseTableMixin):
	__tablename__ = 'ThoughtsViewed'	
	thought_id = Column('thought_id', Integer, ForeignKey("ThoughtsCreated.thought_id"), nullable=False, index=True )				





class CourseMixin(BaseTableMixin):
	course_id = Column('course_id', String(64), nullable=False, index=True)
	
	@declared_attr
	def __table_args__(cls):
		return (Index('ix_%s_user_course' % cls.__tablename__, 'user_id', 'course_id'),)

class ResourceMixin(CourseMixin):
	resource_id = Column('resource_id', String(1048), nullable=False)
	
class ResourceViewMixin(ResourceMixin):
	context_path = Column('context_path', String(1048), nullable=False)

# Time length in seconds
class TimeLengthMixin(object):
	time_length = Column('time_length', Integer)
	
class DeletedMixin(object):
	deleted = Column('deleted', DateTime)



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
	
class NotesCreated(Base,ResourceMixin,DeletedMixin):	
	__tablename__ = 'NotesCreated'
	note_id = Column('note_id', Integer, nullable=False, index=True )
	sharing = Column('sharing', Enum( 'PUBLIC', 'PRIVATE', 'COURSE_ONLY' ), nullable=False )

class NotesViewed(Base,ResourceMixin):	
	__tablename__ = 'NotesViewed'
	note_id = Column('note_id', Integer, ForeignKey("NotesCreated.note_id"), nullable=False, index=True )

class HighlightsCreated(Base,ResourceMixin,DeletedMixin):
	__tablename__ = 'HighlightsCreated'
	note_id = Column('highlight_id', Integer, nullable=False, index=True )

class ForumsCreated(Base,CourseMixin,DeletedMixin):		
	__tablename__ = 'ForumsCreated'
	forum_id = Column('forum_id', Integer, primary_key=True, index=True)				

class ForumMixin(CourseMixin):
	@declared_attr
	def forum_id(cls):
		return Column('forum_id', Integer, ForeignKey("ForumsCreated.forum_id"), nullable=False)
	
class DiscussionsCreated(Base,ForumMixin,DeletedMixin):	
	__tablename__ = 'DiscussionsCreated'
	discussion_id = Column('discussion_id', Integer, primary_key=True ) 
	
class DiscussionMixin(ForumMixin):	
	@declared_attr
	def discussion_id(cls):
		return Column('discussion_id', Integer, ForeignKey("DiscussionsCreated.discussion_id"), nullable=False)

class DiscussionsViewed(Base,DiscussionMixin,TimeLengthMixin):
	__tablename__ = 'DiscussionsViewed'	



class CommentsMixin(DiscussionMixin,DeletedMixin):
	# comment_id should be the DS intid
	@declared_attr
	def comment_id(cls):
		return Column('comment_id', Integer, nullable=False)
	
	# parent_id should point to a parent comment, top-level comments will have null parent_ids
	@declared_attr
	def parent_id(cls):
		return Column('parent_id', Integer)

class ForumCommentsCreated(Base,CommentsMixin):
	__tablename__ = 'ForumCommentsCreated'		
	
class BlogCommentsCreated(Base,CommentsMixin):
	__tablename__ = 'BlogCommentsCreated'	
	
class NoteCommentsCreated(Base,CommentsMixin):
	__tablename__ = 'NoteCommentsCreated'			



class CourseCatalogViews(Base,CourseMixin,TimeLengthMixin):	
	__tablename__ = 'CourseCatalogViews'
		
	
# TODO how will we populate this, at migration time based on client?	
# or perhaps statically at first.
class EnrollmentTypes(Base):
	__tablename__ = 'EnrollmentTypes'
	type_id = Column( 'type_id', Integer, Sequence( 'enrollment_type_seq' ), nullable=False, primary_key=True )
	type_name = Column( 'type_name', String(64), nullable=False, index=True, unique=True )
		
# Dropped is redundant, but it may be useful to grab all course enrollment information here.		
class CourseEnrollments(Base,CourseMixin):
	__tablename__ = 'CourseEnrollments'
	type_id = Column( 'type_id', Integer, ForeignKey( 'EnrollmentTypes.type_id' ), nullable=False )
	dropped = Column( 'dropped', Boolean, nullable=False, default=False )
	
class CourseDrops(Base,CourseMixin):	
	__tablename__ = 'CourseDrops'

class AssignmentMixin(CourseMixin,TimeLengthMixin):
	assignment_id = Column('assignment_id', String(1048), nullable=False, index=True )
		
class SelfAssessmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'SelfAssessmentsTaken'
	submission_id = Column('submission_id', Integer, Sequence( 'self_assess_submission_id_seq' ), primary_key=True, index=True)
		
# TODO Should feedback have its own event tracking? It's one of the few mutable fields if not.
class AssignmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'AssignmentsTaken'
	grade = Column('grade', String(256))
	feedback_count = Column('feedback_count', Integer)
	submission_id = Column('submission_id', Integer, Sequence( 'assignment_submission_id_seq' ), primary_key=True, index=True)


class SubmissionMixin(AssignmentMixin):
	@declared_attr
	def question_id(cls):
		return Column('question_id', Integer, nullable=False)
	
	@declared_attr
	def question_part(cls):
		return Column('question_part', Integer, nullable=False)
	
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
	submission_id = Column('submission_id', Integer, ForeignKey("AssignmentsTaken.submission_id"), nullable=False)

class SelfAssessmentDetails(Base,SubmissionMixin):	
	__tablename__ = 'SelfAssessmentDetails'
	submission_id = Column('submission_id', Integer, ForeignKey("SelfAssessmentsTaken.submission_id"), nullable=False)




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
		
		