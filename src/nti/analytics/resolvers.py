#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component

from nti.app.assessment.interfaces import ICourseAssessmentItemCatalog
from nti.app.assessment.interfaces import ICourseAssignmentCatalog
from nti.assessment.interfaces import IQAssignment
from nti.assessment.interfaces import IQuestionSet

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibraryModifiedOnSyncEvent
from nti.contentlibrary.indexed_data.interfaces import IAudioIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IRelatedContentIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import ISlideDeckIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import ITimelineIndexedDataContainer

from nti.externalization.externalization import to_external_ntiid_oid

from nti.ntiids.ntiids import find_object_with_ntiid
from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import TYPE_UUID
from nti.ntiids.ntiids import TYPE_INTID
from nti.ntiids.ntiids import is_ntiid_of_types

from nti.analytics import get_factory
from nti.analytics import SESSIONS_ANALYTICS

from nti.analytics.common import process_event

## FIXME Need tests

CONTAINER_IFACES = (IRelatedContentIndexedDataContainer,
					IVideoIndexedDataContainer,
					IAudioIndexedDataContainer,
					ISlideDeckIndexedDataContainer,
					ITimelineIndexedDataContainer)

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SESSIONS_ANALYTICS )

# XXX: Copied from nti.app.products.coursewarereports
def _get_self_assessments_for_course(course):
	"""
	Given an :class:`.ICourseInstance`, return a list of all
	the \"self assessments\" in the course. Self-assessments are
	defined as top-level question sets that are not used within an assignment
	in the course.
	"""
	# NOTE: This is pretty tightly coupled to the implementation
	# and the use of one content package (?). See NonAssignmentsByOutlineNodeDecorator
	# (TODO: Find a way to unify this)
	catalog = ICourseAssessmentItemCatalog(course)

	# Not only must we filter out assignments, we must filter out the
	# question sets that they refer to; we assume such sets are only
	# used by the assignment.
	# XXX FIXME not right.

	result = list()

	qsids_to_strip = set()

	for item in catalog.iter_assessment_items():
		if IQAssignment.providedBy(item):
			qsids_to_strip.add(item.ntiid)
			for assignment_part in item.parts:
				question_set = assignment_part.question_set
				qsids_to_strip.add(question_set.ntiid)
				for question in question_set.questions:
					qsids_to_strip.add(question.ntiid)
		elif not IQuestionSet.providedBy(item):
			qsids_to_strip.add(item.ntiid)
		else:
			result.append(item)

	# Now remove the forbidden
	result = [x for x in result if x.ntiid not in qsids_to_strip]
	return result

def _check_ntiid(ntiid):
	result = ntiid and not is_ntiid_of_types(ntiid, (TYPE_OID, TYPE_UUID, TYPE_INTID))
	return bool(result)

def _indexed_data( unit, iface, accum ):
	container = iface(unit, None)
	if not container:
		return
	for item in container.get_data_items():
		ntiid = None
		for name in ('target-ntiid', 'ntiid'):
			t_ntiid = item.get(name)
			if _check_ntiid(t_ntiid):
				ntiid = t_ntiid
				break
		if ntiid:
			accum.add( ntiid )

def recur_children_ntiid_for_unit( node, accum=None ):
	# ContentUnits only
	# TODO Do we not have to check children?
	result = set() if accum is None else accum
	def _recur( node, accum ):
		accum.add( node.ntiid )
		for iface in CONTAINER_IFACES:
			_indexed_data( node, iface, accum )

	_recur( node, result )
	return result

def recur_children_ntiid( node, accum=None ):
	# Content packages only
	result = set() if accum is None else accum

	def _recur( node, accum ):
		accum.add( node.ntiid )

		for iface in CONTAINER_IFACES:
			_indexed_data( node, iface, accum )
		# parse children
		for child in node.children:
			_recur( child, accum )
	_recur( node, result )
	return result

def _get_self_assessment_ids_for_course( course ):
	self_assessments = _get_self_assessments_for_course(course)
	self_assessment_qsids = {x.ntiid: x for x in self_assessments}
	return self_assessment_qsids

def _get_assignment_ids_for_course( course ):
	assignment_catalog = ICourseAssignmentCatalog( course )
	assignment_ids = {asg.ntiid for asg in assignment_catalog.iter_assignments()}
	return assignment_ids

def _do_get_containers_in_course( course ):
	try:
		packages = course.ContentPackageBundle.ContentPackages
	except AttributeError:
		packages = (course.legacy_content_package,)

	containers_in_course = set()
	for package in packages:
		recur_children_ntiid( package, containers_in_course )

	# Add in our self-assessments
	# We filter out questions in assignments here for some reason
	catalog = ICourseAssessmentItemCatalog(course)
	containers_in_course = containers_in_course.union( [x.ntiid for x in catalog.iter_assessment_items()] )

	self_assessments = _get_self_assessments_for_course(course)
	self_assessment_containerids = {x.__parent__.ntiid for x in self_assessments}
	self_assessment_qsids = {x.ntiid: x for x in self_assessments}
	containers_in_course = containers_in_course.union( self_assessment_containerids )
	containers_in_course = containers_in_course.union( self_assessment_qsids )

	#Add in our assignments
	assignment_ids = _get_assignment_ids_for_course( course )
	containers_in_course = containers_in_course.union( assignment_ids )
	containers_in_course.discard( None )

	return containers_in_course

def _build_ntiid_map():
	course_dict = dict()

	start_time = time.time()
	logger.info( 'Initializing course ntiid resolver' )

	catalog = component.getUtility( ICourseCatalog )
	for entry in catalog.iterCatalogEntries():
		course = ICourseInstance( entry )

		containers = _do_get_containers_in_course( course )
		course_key = to_external_ntiid_oid( course )
		course_dict[course_key] = containers

	logger.info( 'Finished initializing course ntiid resolver (%ss) (course_count=%s)',
				time.time() - start_time,
				len( course_dict ) )
	return course_dict

class _CourseFromChildNTIIDResolver(object):

	def __init__(self):
		self.course_to_containers = None

	def reset(self):
		# We may have a few of these come in at once, one
		# per each content package changed.  Let's just empty
		# ourselves out, and reset for the next read.  We build
		# relatively cheaply (6s locally, 9.2014), and the sync
		# events probably only occur during lulls.
		if self.course_to_containers is not None:
			logger.info( 'Resetting analytics course resolver.' )
		self.course_to_containers = None

	def _rebuild(self):
		self.course_to_containers = _build_ntiid_map()

	def get_course(self, container_id):
		course_to_containers = self.course_to_containers

		if course_to_containers is None:
			self._rebuild()
			course_to_containers = self.course_to_containers

		# This is about 4x faster in the worst case than dynamically iterating
		# through children and searching for contained objects (but costs in other ways).
		for course_key, containers in course_to_containers.items():

			# We can no longer check the catalog due to timing issues,
			# but this may be a proper solution anyways.
			if container_id in containers:
				course = find_object_with_ntiid( course_key )
				return course
		return None

_course_from_ntiid_resolver = None

def _get_course_from_ntiid_resolver():
	global _course_from_ntiid_resolver
	if _course_from_ntiid_resolver is None:
		_course_from_ntiid_resolver = _CourseFromChildNTIIDResolver()
	return _course_from_ntiid_resolver

def _reset():
	_get_course_from_ntiid_resolver().reset()

@component.adapter( IContentPackageLibraryModifiedOnSyncEvent )
def _library_sync(event):
	process_event( _get_job_queue, _reset )

def get_course_by_container_id( container_id ):
	"""
	Given a container id, returns the first course found that contains this id.
	This can be fairly expensive if the cache is not built, and is mainly used
	in the standalone analytics process.
	"""

	# Some content is only accessible from the global content
	# package.  During migration, we'll need to (in most cases)
	# check there first, before falling back to checking our current
	# site.  Once the migration is complete, we should default to
	# our current site in the fast lane.

	# Update: JZ: TODO do we still need to check our global site for site packages?
	result = _get_course_from_ntiid_resolver().get_course( container_id )
	return result

get_course_for_ntiid = get_course_by_container_id

def get_root_context( obj ):
	"""
	Given a object with a 'containerId' or 'ntiid', find the root context of the object.
	This will *attempt* to find the course container for the
	given ntiid.  If none found, the root context package will
	be returned.
	"""
	ntiid = getattr( obj, 'containerId',
					getattr( obj, 'ntiid', None ))
	if not ntiid:
		# Should not happen.
		raise TypeError( "No containerId or ntiid found for obj (%s)" % obj )

	result = get_course_by_container_id( ntiid )

	if result is None:
		# Ok, not a course (apparently), see if we're a content package.
		result = find_object_with_ntiid( ntiid )

		if 		result is None \
			or 	not IContentPackage.providedBy( result ):
			raise TypeError( "No course/content-package found for ntiid (%s)" % ntiid )

	return result
