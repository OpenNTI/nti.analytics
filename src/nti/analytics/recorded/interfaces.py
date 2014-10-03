#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.container.interfaces import IContained
from zope.interface.interfaces import ObjectEvent, IObjectEvent

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import	ICourseCatalogEntry

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IUser
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.utils.property import alias

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant

class IObjectViewedRecordedEvent(IObjectEvent):
	user = Object(IUser, title="user that viewed object")
	timestamp = Number(	title=u"The timestamp when this event occurred",
						default=0.0,
						required=False )
	session = interface.Attribute("analytics session")
		
@interface.implementer(IObjectViewedRecordedEvent)
class ObjectViewedRecordedEvent(ObjectEvent):

	def __init__(self, user, obj, timestamp=None, session=None):
		super(ObjectViewedRecordedEvent, self).__init__(obj)
		self.user = user
		self.session = session
		self.timestamp = timestamp or 0.0
		
class INoteViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(INote, title="note viewed", required=True)
	course = Object(ICourseInstance, title="course", required=False)

class ITopicViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(ITopic, title="topic viewed", required=True)
	course = Object(ICourseInstance, title="course", required=False)
	
class ICatalogViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Variant((Object(ICourseInstance, title="the course"),
					  Object(ICourseCatalogEntry, title="the course entry")), 
					 title="course/catalog viewed", required=True)
	
class IBlogViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(IContained, title="blog viewed", required=True)

@interface.implementer(INoteViewedRecordedEvent)
class NoteViewedRecordedEvent(ObjectViewedRecordedEvent):

	note = alias('object')
	
	def __init__(self, user, note, course=None, timestamp=None, session=None):
		super(NoteViewedRecordedEvent, self).__init__(user, note, timestamp)
		self.course = course
		self.session = session
		
@interface.implementer(ITopicViewedRecordedEvent)
class TopicViewedRecordedEvent(ObjectViewedRecordedEvent):

	topic = alias('object')
	
	def __init__(self, user, topic, course=None, timestamp=None, session=None):
		super(TopicViewedRecordedEvent, self).__init__(user, topic, timestamp)
		self.course = course
		self.session = session

@interface.implementer(IBlogViewedRecordedEvent)
class BlogViewedRecordedEvent(ObjectViewedRecordedEvent):

	blog = alias('object')
	
	def __init__(self, user, blog, timestamp=None, session=None):
		super(BlogViewedRecordedEvent, self).__init__(user, blog, timestamp)
		self.session = session

@interface.implementer(ICatalogViewedRecordedEvent)
class CatalogViewedRecordedEvent(ObjectViewedRecordedEvent):

	catalog = course = alias('object')
	
	def __init__(self, user, course, timestamp=None, session=None):
		super(CatalogViewedRecordedEvent, self).__init__(user, course, timestamp)
		self.session = session
