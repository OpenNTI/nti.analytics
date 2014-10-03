#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.interface.interfaces import ObjectEvent, IObjectEvent

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IUser
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.utils.property import alias

from nti.schema.field import Number
from nti.schema.field import Object

class IObjectViewedRecordedEvent(IObjectEvent):
	user = Object(IUser, title="user that viewed object")
	timestamp = Number(	title=u"The timestamp when this event occurred",
						default=0.0,
						required=False )
		
@interface.implementer(IObjectViewedRecordedEvent)
class ObjectViewedRecordedEvent(ObjectEvent):

	def __init__(self, user, obj, timestamp=None):
		super(ObjectViewedRecordedEvent, self).__init__(obj)
		self.user = user
		self.timestamp = timestamp or 0.0
		
class INoteViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(INote, title="note viewed", required=True)
	course = Object(ICourseInstance, title="course", required=False)
	session = interface.Attribute("user session")

class ITopicViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(ITopic, title="note viewed", required=True)
	course = Object(ICourseInstance, title="course", required=False)
	session = interface.Attribute("user session")
	
@interface.implementer(INoteViewedRecordedEvent)
class NoteViewedRecordedEvent(ObjectViewedRecordedEvent):

	note = alias('object')
	
	def __init__(self, user, note, timestamp=None, course=None, session=None):
		super(NoteViewedRecordedEvent, self).__init__(user, note, timestamp)
		self.course = course
		self.session = session
		
@interface.implementer(ITopicViewedRecordedEvent)
class TopicViewedRecordedEvent(ObjectViewedRecordedEvent):

	topic = alias('object')
	
	def __init__(self, user, topic, timestamp=None, course=None, session=None):
		super(TopicViewedRecordedEvent, self).__init__(user, topic, timestamp)
		self.course = course
		self.session = session
