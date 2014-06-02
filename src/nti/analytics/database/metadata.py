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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr

from sqlalchemy.orm import relationship

Base = declarative_base()

class Users(Base):
	__tablename__ = 'users'
	user_id = Column('user_id', Integer, primary_key=True)
	username = Column('username', String(64), nullable=False)
	
# TODO timezone?	
	
class Sessions(Base):
	__tablename__ = 'sessions'
	session_id = Column('session_id', Integer, primary_key=True)
	user_id = Column('user_id', Integer, ForeignKey("users.user_id") )
	ip_addr = Column('ip_addr', String(64) )	
	version = Column('version', String(64) )
	timestamp = Column('timestamp', DateTime)


class BaseTableMixin(object):
	# We could default the timestamp to the current time, but we may have insertion lag.
	@declared_attr
	def session_id(cls):
		return Column('session_id', Integer, ForeignKey("sessions.session_id"), primary_key=True )
	
	@declared_attr
	def user_id(cls):
		return Column('user_id', Integer, ForeignKey("users.user_id"), primary_key=True )
	
	timestamp = Column('timestamp', DateTime, primary_key=True )


# TODO combo keys here?
# TODO how about inverse here? (contact_removed, groups_destroyed?)
# TODO do social elements have course context?
# This information needs to be obscured to protect privacy.	

class ChatsInitiated(Base,BaseTableMixin):
	__tablename__ = 'chats_initiated'

class ChatsJoined(Base,BaseTableMixin):
	__tablename__ = 'chats_joined'
	
class GroupsCreated(Base,BaseTableMixin):
	__tablename__ = 'groups_created'
	
class DistributionListsCreated(Base,BaseTableMixin):
	__tablename__ = 'distibution_lists_created'
	
class ContactsAdded(Base,BaseTableMixin):
	__tablename__ = 'contacts_added'
	
class ContactsRemoved(Base,BaseTableMixin):
	__tablename__ = 'contacts_removed'
	
class ThoughtsCreated(Base,BaseTableMixin):
	__tablename__ = 'thoughts_created'	
	
class ThoughtsViewed(Base,BaseTableMixin):
	__tablename__ = 'thoughts_viewed'					

class CourseMixin(BaseTableMixin):
	course_id = Column('course_id', String(64) )

class ResourceMixin(CourseMixin):
	resource_id = Column('resource_id', String(1048))
	
class ResourceViewMixin(ResourceMixin):
	context_path = Column('context_path', String(1048))

class TimeLengthMixin(object):
	time_length = Column('time_length', Integer)

# For meta-views into synthetic course info, we can special type the resource_id:
#	(about|instructors|tech_support)	
class CourseResourceViews(Base,ResourceViewMixin,TimeLengthMixin):
	__tablename__ = 'course_resource_views'	

# TODO Would we query on these separate event types? Probably not.
# 	If so, we may break them out into separate tables.	
# TODO how about calculating the intervals?
class VideoEvents(Base,ResourceViewMixin):
	__tablename__ = 'video_events'
	video_event_type = Column('video_event_type', Enum( 'WATCH', 'SKIP' ) )
	video_start_time = Column('video_start_time', DateTime )
	video_end_time = Column('video_end_time', DateTime )
	with_transcript = Column('with_transcript', Boolean )
	
class NotesCreated(Base,ResourceMixin):	
	__tablename__ = 'notes_created'
	sharing = Column('sharing', String(16) ) #PUBLIC|PRIVATE|COURSE_ONLY	

# TODO time_length?
class NotesViewed(Base,ResourceMixin):	
	__tablename__ = 'notes_viewed'

class HighlightsCreated(Base,ResourceMixin):
	__tablename__ = 'highlights_created'

class ForumsCreated(Base,CourseMixin):		
	__tablename__ = 'forums_created'
	# TODO unique
	forum_id = Column('forum_id', String(256), primary_key=True)				


class ForumMixin(CourseMixin):
	#TODO is it necessary to have these foreign_keys?
	@declared_attr
	def forum_id(cls):
		return Column('forum_id', Integer, ForeignKey("forums_created.forum_id"))
	
class DiscussionsCreated(Base,ForumMixin):	
	__tablename__ = 'discussions_created'
	discussion_id = Column('discussion_id', String(256), primary_key=True ) 
	
class DiscussionMixin(ForumMixin):	
	@declared_attr
	def discussion_id(cls):
		return Column('discussion_id', Integer, ForeignKey("discussions_created.discussion_id"))

class DiscussionsViewed(Base,DiscussionMixin,TimeLengthMixin):
	__tablename__ = 'discussions_viewed'	

class CommentsCreated(Base,DiscussionMixin):
	__tablename__ = 'comments_created'		

class CourseCatalogViews(Base,CourseMixin):	
	#TODO time_length?	
	__tablename__ = 'course_catalog_views'
		
	
# TODO Do we want instructors here at all?
#	If not, we just have for_credit and non_credit		
# Is dropped redundant?  It may be useful to grab all course enrollment information here.		
class CourseEnrollments(Base,CourseMixin):
	__tablename__ = 'course_enrollments'
	for_credit = Column('for_credit', Boolean )
	dropped = Column('dropped', Boolean )
	
class CourseDrops(Base,CourseMixin):	
	__tablename__ = 'course_drops'

class AssignmentMixin(CourseMixin,TimeLengthMixin):
	assignment_id = Column('assignment_id', String(1048))
		
# Self-assessments too				
# Self-assessments may have retakes; so may assignments.	
# TODO Should feedback have its own event tracking?
#	It's one of the few mutable fields if not.
class AssignmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'assignments_taken'
	grade = Column('grade', String(256))
	feedback_count = Column('feedback_count', Integer)

# TODO How do we do this with retakes, is it important to distinguish?		
#	Perhaps we need to generate a unique id here that maps to assignment_details.
# TODO Can we rely on these parts/ids being integers?
class AssignmentDetails(Base,AssignmentMixin):	
	__tablename__ = 'assignment_details'
	question_id = Column('question_id', Integer)
	question_part = Column('question_part', Integer)
	submission = Column('submission', String(1048)) #(Freeform|MapEntry|Index|List)
	is_correct = Column('is_correct', Boolean)






## TODO LIST
#	examine String limits
#		TODO Should we use TEXT instead of String?
#	parent id (comments, replies, etc)
#	indexes
#	sequence
#	constraint
#	nullable fields

# TODO uid should come from DS
# 	if so, we don't need any other identification, or this table perhaps
#	if not, we should map the DS id to a obfuscated id here.

# Timestamps TEXT here?

class AnalyticsMetadata(object): 

	def __init__(self,engine):
		logger.info( "Initializing database" )	
		Base.metadata.create_all(engine)
		
		