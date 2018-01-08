#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import urlparse

from zope import component

from zope.event import notify

from nti.analytics import SOCIAL_ANALYTICS
from nti.analytics import BLOG_VIEW_ANALYTICS
from nti.analytics import NOTE_VIEW_ANALYTICS
from nti.analytics import TOPIC_VIEW_ANALYTICS
from nti.analytics import VIDEO_VIEW_ANALYTICS
from nti.analytics import CATALOG_VIEW_ANALYTICS
from nti.analytics import RESOURCE_VIEW_ANALYTICS

from nti.analytics import get_factory
from nti.analytics import get_current_username

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IBlogViewEvent
from nti.analytics.interfaces import INoteViewEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import ITopicViewEvent
from nti.analytics.interfaces import ISurveyViewEvent
from nti.analytics.interfaces import ICourseCatalogViewEvent
from nti.analytics.interfaces import IVideoPlaySpeedChangeEvent
from nti.analytics.interfaces import IAssignmentViewEvent
from nti.analytics.interfaces import ISelfAssessmentViewEvent
from nti.analytics.interfaces import IProfileViewEvent
from nti.analytics.interfaces import IProfileActivityViewEvent
from nti.analytics.interfaces import IProfileMembershipViewEvent
from nti.analytics.interfaces import AnalyticsEventValidationError

from nti.analytics.common import get_entity
from nti.analytics.common import process_event

from nti.analytics.sessions import get_nti_session_id

from nti.analytics.database import blogs as db_blogs
from nti.analytics.database import boards as db_boards
from nti.analytics.database import enrollments as db_enrollments
from nti.analytics.database import resource_tags as db_resource_tags
from nti.analytics.database import resource_views as db_resource_views
from nti.analytics.database import assessments as db_assess_views
from nti.analytics.database import profile_views as db_profile_views
from nti.analytics.database import surveys as db_survey_views

from nti.analytics.database.resource_views import get_active_users_with_resource_views as db_get_active_users_with_resource_views
from nti.analytics.database.resource_views import get_active_users_with_video_views as db_get_active_users_with_video_views
from nti.analytics.database.users import get_user

from nti.analytics.progress import get_progress_for_resource_views
from nti.analytics.progress import get_progress_for_video_views
from nti.analytics.progress import get_progress_for_resource_container

from nti.analytics.recorded import VideoSkipRecordedEvent
from nti.analytics.recorded import BlogViewedRecordedEvent
from nti.analytics.recorded import NoteViewedRecordedEvent
from nti.analytics.recorded import VideoWatchRecordedEvent
from nti.analytics.recorded import TopicViewedRecordedEvent
from nti.analytics.recorded import ProfileViewedRecordedEvent
from nti.analytics.recorded import CatalogViewedRecordedEvent
from nti.analytics.recorded import ResourceViewedRecordedEvent
from nti.analytics.recorded import ProfileActivityViewedRecordedEvent
from nti.analytics.recorded import ProfileMembershipViewedRecordedEvent

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageBundle

from nti.dataserver.interfaces import IEntity

from nti.ntiids import ntiids

logger = __import__('logging').getLogger(__name__)

get_resource_views = db_resource_views.get_resource_views
get_user_resource_views = db_resource_views.get_user_resource_views
get_user_resource_views_for_ntiid = db_resource_views.get_user_resource_views_for_ntiid
get_video_views = db_resource_views.get_user_video_views
get_user_video_views = db_resource_views.get_user_video_views
get_video_views_for_ntiid = db_resource_views.get_video_views_for_ntiid
get_resource_views_for_ntiid = db_resource_views.get_resource_views_for_ntiid


def get_active_users_with_resource_views(**kwargs):
	for user_id, count in db_get_active_users_with_resource_views(**kwargs):
		user = get_user(user_id)
		if user:
			yield user, count


def get_active_users_with_video_views(**kwargs):
	for user_id, count in db_get_active_users_with_video_views(**kwargs):
		user = get_user(user_id)
		if user:
			yield user, count


def _has_href_fragment( node, children ):
	def _has_frag( node ):
		return urlparse.urldefrag( node.href )[1]
	# A fragment if we have a frag or if any of our children do
	return bool( 	_has_frag( node )
				or 	_has_frag( next( iter( children ))))


def _is_page_container( node ):
	# Node is only page container if it has children and
	# does not have a fragment in its href.
	children = getattr( node, 'children', None )
	return bool( children and not _has_href_fragment( node, children ) )


def get_progress_for_ntiid( user, resource_ntiid ):
	obj = _get_object( resource_ntiid )
	if _is_page_container( obj ):
		# Top level container with pages (?)
		child_views_dict = {}
		# TODO Some clients might be sending in view events for the container itself
		# instead of the first page.  We add that in, even through it might
		# disturb the accuracy of our results.
		parent_views = get_user_resource_views_for_ntiid( user, obj.ntiid )
		child_views_dict[obj.ntiid] = parent_views

		for child in obj.children:
			child_views = get_user_resource_views_for_ntiid( user, child.ntiid )
			child_views_dict[child.ntiid] = child_views
		result = get_progress_for_resource_container( resource_ntiid, child_views_dict )
	else:
		# Not sure if one of these is more expensive than the other.  Perhaps
		# the caller would be able to specify video or other?
		resource_views = get_user_resource_views_for_ntiid( user, resource_ntiid )

		if resource_views:
			result = get_progress_for_resource_views( resource_ntiid, resource_views )

		else:
			resource_views = db_resource_views.get_user_video_views_for_ntiid( user, resource_ntiid )
			result = get_progress_for_video_views( resource_ntiid, resource_views )

	return result


def get_video_progress_for_course( user, course ):
	"""
	For a given user/course, return a collection of progress for all videos we have on record.
	"""
	resource_views = get_user_video_views( user, course )
	view_dict = {}

	for resource_view in resource_views:
		view_dict.setdefault( resource_view.ResourceId, [] ).append( resource_view )

	result = [get_progress_for_video_views( ntiid, events ) for ntiid, events in view_dict.items()]
	return result


def _get_object( ntiid ):
	return ntiids.find_object_with_ntiid( ntiid )


def _get_course( event ):
	__traceback_info__ = event.RootContextID
	result = _get_object( event.RootContextID )
	# Global course info objects have an HTML ntiid
	if result is None:
		catalog = component.queryUtility(ICourseCatalog)
		if catalog is not None:
			result = catalog.getCatalogEntry(event.RootContextID)
	# Course catalog views may resolve to catalog entries
	# If not a course, return what we have (e.g. ContentPackage)
	return ICourseInstance( result, result )


def _get_root_context( event ):
	result = _get_object( event.RootContextID )
	if not IEntity.providedBy( result ):
		result = _get_course( event )
	return result


def _validate_analytics_event( event, object_id=None ):
	"""
	Validate our events, sanitizing as we go.
	"""
	if object_id:
		# Cannot do much without an object; probably deleted.
		# Ideally, we need to capture all id related data
		# before the event is queued, but that is no guarantee
		# that the event gets to us in time.
		obj = _get_object( object_id )
		if obj is None:
			raise UnrecoverableAnalyticsError(
						'Event received for deleted object (id=%s) (event=%s)' %
						( object_id, event ) )

	# I think nti.externalization handles encoding.
	user = get_entity( event.user )
	if user is None:
		raise UnrecoverableAnalyticsError(
							'Event received with non-existent user (user=%s) (event=%s)' %
							( event.user, event ) )

	time_length = getattr( event, 'Duration', None )
	# None durations may indicate an event start. So we keep them.
	# If we have zero second events, we ignore them.
	if time_length and time_length <= 0:
		raise UnrecoverableAnalyticsError(
							"""Event received with negative time_length
							(user=%s) (time_length=%s) (event=%s)""" %
							( event.user, time_length, event ) )

	event.time_length = time_length and int( time_length )


def _valid_course_type( obj ):
	return ICourseInstance.providedBy( obj ) \
		or IContentPackageBundle.providedBy( obj ) \
		or IContentPackage.providedBy( obj )


def _valid_root_context_type( obj ):
	return IEntity.providedBy( obj ) \
		or _valid_course_type( obj )


def _validate_root_context_event( event, object_id=None ):
	"""
	Validate we have a root context (course or entity).
	"""
	# XXX: We could get the course(s) from the resource id (asset), and then
	# we could probably guess based on a course the event creator is enrolled in.
	_validate_analytics_event( event, object_id )

	root_context = _get_root_context( event )
	if 		root_context is None \
		or 	not _valid_root_context_type( root_context ):
		raise ValueError( u"""Event received with non-existent root context id
							(user=%s) (RootContextID=%s) (event=%s)""" %
							( event.user, event.RootContextID, event ) )


def _validate_course_event( event, object_id=None ):
	"""
	Validate we have a course.
	"""
	_validate_analytics_event( event, object_id )

	course = _get_course( event )
	if 		course is None \
		or 	not _valid_course_type( course ):
		raise ValueError( u"""Event received with non-existent course id
							(user=%s) (course=%s) (event=%s)""" %
							( event.user, event.RootContextID, event ) )


def _validate_resource_event( event ):
	""" Validate our events, sanitizing as we go. """
	_validate_root_context_event( event )

	if not ntiids.is_valid_ntiid_string( event.resource_id ):
		raise UnrecoverableAnalyticsError(
							"""Event received for invalid resource id
							(user=%s) (resource=%s) (event=%s)""" %
							( event.user, event.resource_id, event ) )


def _validate_play_speed_event( event ):
	"""
	Validate our events, sanitizing as we go.
	"""
	_validate_resource_event( event )

	old_play_speed = event.OldPlaySpeed
	new_play_speed = event.NewPlaySpeed

	if 	old_play_speed == new_play_speed:
		raise UnrecoverableAnalyticsError(
					u'PlaySpeed event has invalid time values (old=%s) (new=%s) (event=%s)' %
					( old_play_speed, new_play_speed, event.event_type ) )

	video_time = event.VideoTime

	if video_time < 0:
		raise UnrecoverableAnalyticsError(
						u'Video event has invalid time value (time=%s) (event=%s)' %
						( video_time, event.event_type ) )


def _validate_video_event( event ):
	"""
	Validate our events, sanitizing as we go.
	"""
	# Validate our parent fields
	_validate_resource_event( event )

	start = event.video_start_time
	end = event.video_end_time

	if 		start < 0 	\
		or 	(end is not None and end < 0):
		raise UnrecoverableAnalyticsError(
						u'Video event has invalid time values (start=%s) (end=%s) (event=%s)' %
						( start, end, event.event_type ) )

	# Be lenient if watch time is less than max duration due to the way the player events are triggered.
	max_time_length = event.MaxDuration
	if max_time_length and max_time_length < event.Duration:
		event.Duration = max_time_length

	event.MaxDuration = int( max_time_length ) if max_time_length else None
	event.video_start_time = int( start )
	event.video_end_time = int( end ) if end is not None else None


def _add_note_event( event, nti_session=None ):
	try:
		_validate_root_context_event( event, object_id=event.note_id )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return

	user = get_entity( event.user )
	root_context = _get_root_context( event )
	note = _get_object( event.note_id )

	db_resource_tags.create_note_view(
								user,
								nti_session,
								event.timestamp,
								event.context_path,
								root_context,
								note )

	logger.debug( 	"Course note view event (user=%s) (root_context=%s)",
					user,
					getattr( root_context, '__name__', root_context ) )

	notify(NoteViewedRecordedEvent(	user=user, note=note, timestamp=event.timestamp,
									context=root_context, session=nti_session,
									context_path=event.context_path,
									duration=getattr(event, 'time_length', 1)))


def _add_topic_event( event, nti_session=None ):
	try:
		_validate_root_context_event( event, object_id=event.topic_id )
	except UnrecoverableAnalyticsError as e:
		logger.warn( u'Error while validating event (%s)', e )
		return

	user = get_entity( event.user )
	root_context = _get_root_context( event )
	topic = _get_object( event.topic_id )

	db_boards.create_topic_view(user,
								nti_session,
								event.timestamp,
								root_context,
								event.context_path,
								topic,
								event.time_length )
	logger.debug( 	"Course topic view event (user=%s) (root_context=%s) (topic=%s) (time_length=%s)",
					user,
					getattr( root_context, '__name__', root_context ),
					getattr( topic, '__name__', topic ),
					event.time_length )

	notify(TopicViewedRecordedEvent(user=user, topic=topic, timestamp=event.timestamp,
									context=root_context, session=nti_session,
									duration=event.time_length,
									context_path=event.context_path))


def _add_blog_event( event, nti_session=None ):
	try:
		_validate_analytics_event( event, object_id=event.blog_id )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return

	user = get_entity( event.user )
	blog = _get_object( event.blog_id )

	db_blogs.create_blog_view(	user,
								nti_session,
								event.timestamp,
								event.context_path,
								blog,
								event.time_length )
	logger.debug( 	"Blog view event (user=%s) (blog=%s) (time_length=%s)",
					user, blog, event.time_length )

	notify(BlogViewedRecordedEvent(user=user, blog=blog, timestamp=event.timestamp,
								   session=nti_session,
								   duration=event.time_length,
								   context_path=event.context_path))


def _add_catalog_event( event, nti_session=None ):
	try:
		_validate_course_event( event )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return

	user = get_entity( event.user )
	course = _get_course( event )

	db_enrollments.create_course_catalog_view( user,
								nti_session,
								event.timestamp,
								event.context_path,
								course,
								event.time_length )
	logger.debug( 	"Course catalog view event (user=%s) (course=%s) (time_length=%s)",
					user,
					getattr( course, '__name__', course ),
					event.time_length )

	notify(CatalogViewedRecordedEvent(user=user, context=course, timestamp=event.timestamp,
									  session=nti_session,
									  duration=event.time_length,
									  context_path=event.context_path))


def _do_resource_view( to_call, event, resource_id, nti_session=None, *args ):
	user = get_entity( event.user )
	root_context = _get_root_context( event )

	to_call( user, nti_session, event.timestamp, root_context,
			event.context_path, resource_id, event.time_length, *args )
	logger.debug( 	"Resource view event (user=%s) (root_context=%s) (resource=%s) (time_length=%s)",
					user,
					getattr( root_context, '__name__', root_context ),
					resource_id,
					event.time_length )

	notify(ResourceViewedRecordedEvent(user=user, resource=resource_id, context=root_context,
									   timestamp=event.timestamp, session=nti_session,
									   duration=event.time_length,
									   context_path=event.context_path))


def _validate_assessment_event( event, assess_id ):
	_validate_root_context_event( event )

	if not ntiids.is_valid_ntiid_string( assess_id ):
		raise UnrecoverableAnalyticsError(
							u"""Event received for invalid assessment id
							(user=%s) (assessment_id=%s) (event=%s)""" %
							( event.user, assess_id, event ) )


def _add_resource_event( event, nti_session=None ):
	try:
		_validate_resource_event( event )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return

	_do_resource_view( db_resource_views.create_course_resource_view,
						event, event.resource_id, nti_session )


def _add_self_assessment_event( event, nti_session=None ):
	try:
		_validate_assessment_event( event, event.QuestionSetId )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return
	_do_resource_view(db_assess_views.create_self_assessment_view,
					  event, event.content_id, nti_session, event.QuestionSetId )


def _add_assignment_event( event, nti_session=None ):
	try:
		_validate_assessment_event( event, event.AssignmentId )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return
	_do_resource_view( db_assess_views.create_assignment_view,
					event, event.content_id, nti_session, event.AssignmentId )


def _add_survey_event(event, nti_session=None):
	try:
		_validate_assessment_event(event, event.SurveyId)
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return
	_do_resource_view(db_survey_views.create_survey_view,
					  event, event.content_id, nti_session, event.SurveyId)


def _add_video_event( event, nti_session=None ):
	try:
		_validate_video_event( event )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return

	user = get_entity( event.user )
	resource_id = event.resource_id
	root_context = _get_root_context( event )

	db_resource_views.create_video_event( user,
						nti_session,
						event.timestamp,
						root_context,
						event.context_path,
						resource_id,
						event.time_length,
						event.MaxDuration,
						event.event_type,
						event.video_start_time,
						event.video_end_time,
						event.with_transcript,
						event.PlaySpeed )
	logger.debug( 	"Video event (user=%s) (root_context=%s) (resource=%s) (type=%s) (start=%s) (end=%s) (time_length=%s)",
					user,
					getattr( root_context, '__name__', root_context ),
					resource_id,
					event.event_type, event.video_start_time,
					event.video_end_time, event.time_length )

	if event.event_type == 'WATCH':
		clazz = VideoWatchRecordedEvent
	else:
		clazz = VideoSkipRecordedEvent

	notify(clazz(user=user, video=resource_id,
				 context=root_context,
				 session=nti_session,
				 timestamp=event.timestamp,
				 context_path=event.context_path,
				 duration=event.time_length,
				 video_start_time=event.video_start_time,
				 video_end_time=event.video_end_time,
				 with_transcript=event.with_transcript))


def _add_play_speed_event( event, nti_session=None ):
	try:
		_validate_play_speed_event( event )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return

	user = get_entity( event.user )
	resource_id = event.ResourceId
	root_context = _get_root_context( event )
	video_time = event.VideoTime

	db_resource_views.create_play_speed_event( user,
						nti_session,
						event.timestamp,
						root_context,
						resource_id,
						video_time,
						event.OldPlaySpeed,
						event.NewPlaySpeed )
	logger.debug( 	"PlaySpeed event (user=%s) (root_context=%s) (resource=%s) (old=%s) (new=%s)",
					user,
					getattr( root_context, '__name__', root_context ),
					resource_id,
					event.OldPlaySpeed,
					event.NewPlaySpeed )


def _validate_profile_event( event ):
	_validate_analytics_event( event )
	profile_entity = get_entity( event.ProfileEntity )
	if profile_entity is None:
		raise UnrecoverableAnalyticsError(
							'Event received with non-existent profile user (user=%s) (event=%s)' %
							( event.ProfileEntity, event ) )


def _do_add_profile_event( to_call, event, nti_session=None, recorded=None):
	try:
		_validate_profile_event( event )
	except UnrecoverableAnalyticsError as e:
		logger.warn( 'Error while validating event (%s)', e )
		return
	to_call( event, nti_session )

	if recorded is not None:
		user = get_entity( event.user )
		notify(recorded(user=user, profile=event.ProfileEntity, timestamp=event.timestamp,
						session=nti_session, context_path=event.context_path))


def _add_profile_event( event, nti_session=None ):
	_do_add_profile_event( db_profile_views.create_profile_view,
						   event,
						   nti_session,
						   ProfileViewedRecordedEvent )


def _add_profile_activity_event( event, nti_session=None ):
	_do_add_profile_event( db_profile_views.create_profile_activity_view,
						   event,
						   nti_session,
						   ProfileActivityViewedRecordedEvent )


def _add_profile_membership_event( event, nti_session=None ):
	_do_add_profile_event( db_profile_views.create_profile_membership_view,
						   event,
						   nti_session,
						   ProfileMembershipViewedRecordedEvent )


def _get_profile_queue():
	factory = get_factory()
	return factory.get_queue( SOCIAL_ANALYTICS )


def _get_resource_queue():
	factory = get_factory()
	return factory.get_queue( RESOURCE_VIEW_ANALYTICS )


def _get_video_queue():
	factory = get_factory()
	return factory.get_queue( VIDEO_VIEW_ANALYTICS )


def _get_catalog_queue():
	factory = get_factory()
	return factory.get_queue( CATALOG_VIEW_ANALYTICS )


def _get_topic_queue():
	factory = get_factory()
	return factory.get_queue( TOPIC_VIEW_ANALYTICS )


def _get_blog_queue():
	factory = get_factory()
	return factory.get_queue( BLOG_VIEW_ANALYTICS )


def _get_note_queue():
	factory = get_factory()
	return factory.get_queue( NOTE_VIEW_ANALYTICS )


def handle_events(batch_events, return_invalid=True):
	"""
	Handle resource view events, optionally returning or raising on invalid events
	"""

	validation_errors = []
	for event in batch_events:
		# Try to grab a session, careful not to raise so we don't lose our
		# otherwise valid events. Since the batch send time on the client side
		# is currently 10s, we can reasonably expect a valid session to exist.
		if not event.user:
			event.user = get_current_username()
		nti_session = get_nti_session_id(event=event)

		kwargs = {'event': event,
				  'nti_session': nti_session}

		try:
			if INoteViewEvent.providedBy( event ):
				process_event( _get_note_queue, _add_note_event, **kwargs )
			elif IBlogViewEvent.providedBy( event ):
				process_event( _get_blog_queue, _add_blog_event, **kwargs )
			elif ITopicViewEvent.providedBy( event ):
				process_event( _get_topic_queue, _add_topic_event, **kwargs )
			elif IVideoEvent.providedBy( event ):
				process_event( _get_video_queue, _add_video_event, **kwargs )
			elif ISelfAssessmentViewEvent.providedBy( event ):
				process_event( _get_resource_queue, _add_self_assessment_event, **kwargs )
			elif IAssignmentViewEvent.providedBy( event ):
				process_event( _get_resource_queue, _add_assignment_event, **kwargs )
			elif ISurveyViewEvent.providedBy( event ):
				process_event( _get_resource_queue, _add_survey_event, **kwargs )
			elif IResourceEvent.providedBy( event ):
				process_event( _get_resource_queue, _add_resource_event, **kwargs )
			elif ICourseCatalogViewEvent.providedBy( event ):
				process_event( _get_catalog_queue, _add_catalog_event, **kwargs )
			elif IVideoPlaySpeedChangeEvent.providedBy( event ):
				process_event( _get_video_queue, _add_play_speed_event, **kwargs )
			elif IProfileActivityViewEvent.providedBy( event ):
				process_event( _get_profile_queue, _add_profile_activity_event, **kwargs )
			elif IProfileMembershipViewEvent.providedBy( event ):
				process_event( _get_profile_queue, _add_profile_membership_event, **kwargs )
			elif IProfileViewEvent.providedBy( event ):
				process_event( _get_profile_queue, _add_profile_event, **kwargs )
		except AnalyticsEventValidationError as e:
			if return_invalid:
				# If returning, we want to capture all errors and process the rest.
				validation_errors.append(e)
			else:
				raise
	# If we validated early, we could return something meaningful.
	# But we'd have to handle all validation exceptions as to not lose the valid
	# events. The nti.asynchronous.processor does this and at least drops the bad
	# events in a failed queue.
	return len( batch_events ), validation_errors


class UnrecoverableAnalyticsError(AnalyticsEventValidationError):
	"""
	Event validation errors that the analytics process fundamentally cannot
	recover from. Events with such errors should log the issue and return,
	such that the event will not be re-run in the future.
	"""

	def __init__(self, message):
		self.message = message

	def __str__(self):
		return self.message
