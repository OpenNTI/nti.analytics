#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from collections import OrderedDict

from zope import interface

from nti.analytics_database import CONTEXT_PATH_SEPARATOR

from nti.analytics.database import get_analytics_db

from nti.analytics_database.interfaces import IAnalyticsRootContextResolver

from nti.analytics.database.root_context import get_root_context
from nti.analytics.database.root_context import get_root_context_id

from nti.analytics.database.users import get_user
from nti.analytics.database.users import get_or_create_user

from nti.dataserver.interfaces import IEntity

logger = __import__('logging').getLogger(__name__)


def get_body_text_length(obj):
	"""
	For a given obj with a body, find the length of the textual content.
	"""
	# TODO: We may have client created HTML here. Should we try to strip it?
	text_length = 0
	for item in obj.body or ():
		if not isinstance(item, six.string_types):
			continue
		try:
			text_length += len(item)
		except (AttributeError, TypeError):
			pass
	return text_length


def get_context_path(context_path):
	# Note: we could also sub these resource_ids for the actual
	# ids off of the Resources table.  That would be a bit tricky, because
	# we sometimes have courses and client specific strings (e.g. 'overview')
	# in this collection.
	result = ''
	if context_path:
		# This will remove all duplicate elements. Hopefully we do
		# not have scattered duplicates, which would be an error condition.
		context_path = list(OrderedDict.fromkeys(context_path))
		result = CONTEXT_PATH_SEPARATOR.join(context_path)
		# Cap this length to ensure it fits in our tables
		result = result[:1048]
	return result


def get_root_context_ids(root_context):
	course_id = entity_root_context_id = None
	if IEntity.providedBy(root_context):
		entity = get_or_create_user(root_context)
		entity_root_context_id = entity.user_id
	else:
		db = get_analytics_db()
		course_id = get_root_context_id(db, root_context, create=True)
	return course_id, entity_root_context_id


@interface.implementer(IAnalyticsRootContextResolver)
def get_root_context_obj(root_context_record):
	course_id = root_context_record.course_id
	if course_id:
		root_context = get_root_context(course_id)
	else:
		entity_root_context_id = root_context_record.entity_root_context_id
		root_context = get_user(entity_root_context_id)
	return root_context
