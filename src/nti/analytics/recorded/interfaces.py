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

from dolmen.builtins import IString
from dolmen.builtins import INumeric

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import	ICourseCatalogEntry

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IUser
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.utils.property import alias

from nti.schema.field import Bool
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant

class IObjectViewedRecordedEvent(IObjectEvent):
	user = Object(IUser, title="user that viewed object")
	timestamp = Number(	title=u"The timestamp when this event occurred",
						default=0.0,
						required=False )
	session = interface.Attribute("analytics session")

class INoteViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(INote, title="note viewed", required=True)
	context = Object(ICourseInstance, title="root context", required=False)

class ITopicViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(ITopic, title="topic viewed", required=True)
	context = Variant((Object(IString, title="the context id"),
					   Object(INumeric, title="the context id"),
					   Object(ICourseInstance, title="the context course")), 
					 title="context object", required=False)
	
class ICatalogViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Variant((Object(ICourseInstance, title="the course"),
					  Object(ICourseCatalogEntry, title="the course entry")), 
					 title="course/catalog viewed", required=True)
	
class IBlogViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(IContained, title="blog viewed", required=True)

class IResourceViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(IString, title="resourced viewed", required=True)
	context = Variant((Object(IString, title="the context id"),
					   Object(INumeric, title="the context id"),
					   Object(ICourseInstance, title="the context course")), 
					 title="context object", required=False)
	
class IVideoRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(IString, title="video id", required=True)
	context_path = Object(IString, title="context path", required=False)
	duration = Number(title="Time length duration", required=False, default=0)
	video_start_time = Number(title="Start time (secs)", required=False, default=0)
	video_end_time = Number(title="End time (secs)", required=False, default=0)
	with_transcript = Bool(title="Viewed with a trascript", required=False, default=False)
	context = Variant((Object(IString, title="the context id"),
					   Object(INumeric, title="the context id"),
					   Object(ICourseInstance, title="the context course")), 
					 title="context object", required=False)

class IVideoWatchRecordedEvent(IVideoRecordedEvent):
	pass
	
class IVideoSkipRecordedEvent(IVideoRecordedEvent):
	pass

@interface.implementer(IObjectViewedRecordedEvent)
class ObjectViewedRecordedEvent(ObjectEvent):

	def __init__(self, user, obj, timestamp=None, session=None):
		super(ObjectViewedRecordedEvent, self).__init__(obj)
		self.user = user
		self.session = session
		self.timestamp = timestamp or 0.0

@interface.implementer(INoteViewedRecordedEvent)
class NoteViewedRecordedEvent(ObjectViewedRecordedEvent):

	note = alias('object')
	
	def __init__(self, user, note, context=None, timestamp=None, session=None):
		super(NoteViewedRecordedEvent, self).__init__(user, note, timestamp, session)
		self.context = context
		
@interface.implementer(ITopicViewedRecordedEvent)
class TopicViewedRecordedEvent(ObjectViewedRecordedEvent):

	topic = alias('object')
	
	def __init__(self, user, topic, context=None, timestamp=None, session=None):
		super(TopicViewedRecordedEvent, self).__init__(user, topic, timestamp, session)
		self.context = context

@interface.implementer(IBlogViewedRecordedEvent)
class BlogViewedRecordedEvent(ObjectViewedRecordedEvent):
	
	blog = alias('object')
	
	def __init__(self, user, blog, timestamp=None, session=None):
		super(BlogViewedRecordedEvent, self).__init__(user, blog, timestamp, session)
	
@interface.implementer(ICatalogViewedRecordedEvent)
class CatalogViewedRecordedEvent(ObjectViewedRecordedEvent):

	catalog = course = alias('object')

	def __init__(self, user, context, timestamp=None, session=None):
		super(CatalogViewedRecordedEvent, self).__init__(user, context, timestamp, session)

@interface.implementer(IResourceViewedRecordedEvent)
class ResourceViewedRecordedEvent(ObjectViewedRecordedEvent):
	
	resource = alias('object')
	
	def __init__(self, user, resource, context=None, timestamp=None, session=None):
		super(ResourceViewedRecordedEvent, self).__init__(user, resource, timestamp, session)
		self.context = context

@interface.implementer(IVideoRecordedEvent)
class VideoRecordedEvent(ObjectViewedRecordedEvent):
	
	resource = alias('object')
	time_length = alias('duration')
	
	def __init__(self, user, video, context=None, timestamp=None, session=None,
				 context_path=None, duration=0, video_start_time=0, 
				 video_end_time=0, with_transcript=False):
		super(VideoRecordedEvent, self).__init__(user, video, timestamp, session)
		self.context = context
		self.duration = duration
		self.context_path = context_path
		self.video_end_time = video_end_time
		self.with_transcript = with_transcript
		self.video_start_time = video_start_time
		
@interface.implementer(IVideoWatchRecordedEvent)
class VideoWatchRecordedEvent(VideoRecordedEvent):
	pass
	
@interface.implementer(IVideoSkipRecordedEvent)
class VideoSkipRecordedEvent(VideoRecordedEvent):
	pass

	
