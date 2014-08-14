#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime

from sqlalchemy.schema import Index
from sqlalchemy.ext.declarative import declared_attr

from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import SESSION_COLUMN_TYPE

class BaseTableMixin(object):

	# For migrating data, we may not have sessions (or timestamps); thus this is optional.
	# Does the same apply to users?  Perhaps we don't have a 'creator' stored.
	@declared_attr
	def session_id(cls):
		return Column('session_id', SESSION_COLUMN_TYPE, ForeignKey("Sessions.session_id"), nullable=True )

	@declared_attr
	def user_id(cls):
		return Column('user_id', Integer, ForeignKey("Users.user_id"), index=True, nullable=True )

	timestamp = Column('timestamp', DateTime, nullable=True )

class BaseViewMixin(object):

	# For resource views, we need timestamp to be non-null for primary key purposes.
	# It will have to be fine-grain to avoid collisions.
	@declared_attr
	def session_id(cls):
		return Column('session_id', SESSION_COLUMN_TYPE, ForeignKey("Sessions.session_id"), nullable=True )

	@declared_attr
	def user_id(cls):
		return Column('user_id', Integer, ForeignKey("Users.user_id"), index=True )

	timestamp = Column('timestamp', DateTime)

class DeletedMixin(object):
	deleted = Column('deleted', DateTime)

class CourseMixin(object):
	course_id = Column('course_id', Integer, nullable=False, index=True, autoincrement=False)

	@declared_attr
	def __table_args__(cls):
		return (Index('ix_%s_user_course' % cls.__tablename__, 'user_id', 'course_id'),)

class ResourceMixin(CourseMixin):
	resource_id = Column('resource_id', NTIID_COLUMN_TYPE, nullable=False, index=True)

class ResourceViewMixin(ResourceMixin,BaseViewMixin):
	# FIXME Needs to be defined
	context_path = Column('context_path', String(1048), nullable=False)

# Time length in seconds
class TimeLengthMixin(object):
	time_length = Column('time_length', Integer)

class CommentsMixin(BaseTableMixin,DeletedMixin):
	# comment_id should be the DS intid
	@declared_attr
	def comment_id(cls):
		return Column('comment_id', Integer, nullable=False, autoincrement=False)

	@declared_attr
	def comment_length(cls):
		return Column('comment_length', Integer, nullable=True, autoincrement=False)

	# parent_id should point to a parent comment; top-level comments will have null parent_ids
	@declared_attr
	def parent_id(cls):
		return Column('parent_id', Integer)


