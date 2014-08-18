#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.dataserver.interfaces import IEntity
from nti.intid.interfaces import IIntIdRemovedEvent

from nti.analytics.common import process_event

from nti.analytics.database import users as db_users

from nti.analytics.identifier import UserId
_userid = UserId()

from nti.analytics import get_factory
from nti.analytics import DELETE_ANALYTICS

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( DELETE_ANALYTICS )

def _delete_entity( entity_id ):
	db_users.delete_entity( entity_id )
	logger.info( 'Deleted entity (id=%s)', entity_id )

@component.adapter( IEntity, IIntIdRemovedEvent )
def _entity_removed( entity, event ):
	entity_id = _userid.get_id( entity )
	process_event( _get_job_queue, _delete_entity, entity_id=entity_id )
