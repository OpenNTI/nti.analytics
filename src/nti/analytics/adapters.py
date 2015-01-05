#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapters for application-level events.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.assessment.interfaces import IQAssignment
from nti.assessment.interfaces import IQuestionSet

from nti.dataserver.interfaces import IUser

from nti.analytics.interfaces import IProgress

from nti.analytics.assessments import get_assignment_for_user
from nti.analytics.assessments import get_self_assessments_for_user_and_id

from nti.analytics.progress import DefaultProgress

@interface.implementer( IProgress )
@component.adapter( IUser, IQAssignment )
def _assignment_progress_for_user( user, assignment ):
	"""
	Given an assignment and a user, we
	attempt to determine the amount of progress the user
	has made on the assignment.  If we have nothing in which to
	gauge progress, we return None.
	"""
	# In local tests, about 100 objects are decorated in about 1s;
	# this is in UCOL with a lot of assignments but few assessments.

	# TODO Caching?

	# Is this property always valid?
	assignment_id = getattr( assignment, 'ntiid', None )
	assignment_records = get_assignment_for_user( user, assignment_id )
	result = None
	if assignment_records:
		# Simplistic implementation
		last_mod = max( (x.timestamp for x in assignment_records) )
		result = DefaultProgress( assignment_id, 1, 1, True, last_modified=last_mod )
	return result

@interface.implementer( IProgress )
@component.adapter( IUser, IQuestionSet )
def _assessment_progress_for_user( user, assessment ):
	"""
	Given a generic assessment and a user, we
	attempt to determine the amount of progress the user
	has made on the assignment.  If we have nothing in which to
	gauge progress, we return None.
	"""
	# TODO Caching?
	# To properly check for assignment, we need the course to see
	# what the assignment ntiids are versus the possible self-assessment ids.
	# Maybe we're better off checking for assignment or self-assessment.
	# If we have a cache, the cost is trivial.
	# Or we only care about possible self-assessments here; if we have a record
	# great, else we do not return anything.

	assessment_id = getattr( assessment, 'ntiid', None )
	assessment_records = get_self_assessments_for_user_and_id( user, assessment_id )
	result = None
	if assessment_records:
		# Simplistic implementation
		last_mod = max( (x.timestamp for x in assessment_records) )
		result = DefaultProgress( assessment_id, 1, 1, True, last_modified=last_mod )
	return result

