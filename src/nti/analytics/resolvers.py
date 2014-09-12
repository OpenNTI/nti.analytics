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
from zope.catalog.interfaces import ICatalog

from nti.app.assessment.interfaces import ICourseAssessmentItemCatalog
from nti.app.assessment.interfaces import ICourseAssignmentCatalog
from nti.assessment.interfaces import IQAssignment
from nti.assessment.interfaces import IQuestionSet

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.metadata_index import CATALOG_NAME

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

def _do_get_containers_in_course( course ):
	try:
		packages = course.ContentPackageBundle.ContentPackages
	except AttributeError:
		packages = (course.legacy_content_package,)

	def _recur( node, accum ):
		#Get our embedded ntiids and recursively fetch our children's ntiids
		ntiid = node.ntiid
		accum.update( node.embeddedContainerNTIIDs )
		if ntiid:
			accum.add( ntiid )
		for n in node.children:
			_recur( n, accum )

	containers_in_course = set()
	for package in packages:
		_recur(package, containers_in_course )

	# Add in our self-assessments
	# We filter out questions in assignments here for some reason
	#self_assessments = _get_self_assessments_for_course(self.course)
	catalog = ICourseAssessmentItemCatalog(course)
	containers_in_course = containers_in_course.union( [x.ntiid for x in catalog.iter_assessment_items()] )

	self_assessments = _get_self_assessments_for_course(course)
	self_assessment_containerids = {x.__parent__.ntiid for x in self_assessments}
	self_assessment_qsids = {x.ntiid: x for x in self_assessments}
	containers_in_course = containers_in_course.union( self_assessment_containerids )
	containers_in_course = containers_in_course.union( self_assessment_qsids )

	#Add in our assignments
	assignment_catalog = ICourseAssignmentCatalog( course )
	containers_in_course = containers_in_course.union( ( asg.ntiid for asg in assignment_catalog.iter_assignments() ) )
	containers_in_course.discard( None )

	return containers_in_course

def _build_ntiid_map():
	course_dict = dict()
	start_time = time.time()
	logger.info( 'Initializing course ntiid resolver' )
	from nti.contenttypes.courses.interfaces import ICourseCatalog
	catalog = component.getUtility( ICourseCatalog )
	for entry in catalog.iterCatalogEntries():
		course = ICourseInstance( entry )
		containers = _do_get_containers_in_course( course )
		# FIXME Do we need to store a weakref here? or ntiid?
		course_dict[course] = containers

	logger.info( 'Finished initializing course ntiid resolver (%ss) (course_count=%s)',
				time.time() - start_time,
				len( course_dict ) )
	return course_dict

class _CourseResolver(object):

	def __init__(self):
		self.course_to_containers = _build_ntiid_map()

	def get_md_catalog(self):
		return component.getUtility(ICatalog,CATALOG_NAME)

	# FIXME need to re-build on re-sync

	def get_course(self, object_id):
		# This is about 4x faster in the worst case than dynamically iterating
		# through children and searching for contained objects (but costs in other ways).
		for course, containers in self.course_to_containers.items():
			md_catalog = self.get_md_catalog()
			intids_of_objects_in_course_containers = md_catalog['containerId'].apply({'any_of': containers})
			if object_id in intids_of_objects_in_course_containers:
				return course
		return None

_course_resolver = _CourseResolver()

def get_course_by_object_id(object_id):
	# Some content is only accessible from the global content
	# package.  During migration, we'll need to (in most cases)
	# check there first, before falling back to checking our current
	# site.  Once the migration is complete, we should default to
	# our current site in the fast lane.
	# This is expensive if we do not find our course.

	# Update: JZ: TODO do we still need to check our global site for site packages?
	result = _course_resolver.get_course( object_id )

	if result is None:
		raise TypeError( "No course found for object_id (%s)" % object_id )
	return result

