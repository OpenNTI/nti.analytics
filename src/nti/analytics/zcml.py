#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import schema
from zope import interface
from zope.configuration import fields
from zope.component.zcml import utility

from .neo4j import Neo4jDB
from . import interfaces as graph_interfaces

NEO4J = graph_interfaces.NEO4J
DATABASE_TYPES = graph_interfaces.DATABASE_TYPES

class IRegisterGraphDB(interface.Interface):
	"""
	The arguments needed for registering an graph db
	"""
	name = fields.TextLine(title="db name identifier (site)", required=False, default="")
	url = fields.TextLine(title="db url", required=True)
	dbtype = schema.Choice(title="db type", values=DATABASE_TYPES, default=NEO4J,
						   required=False)
	username = fields.TextLine(title="db username", required=False)
	password = schema.Password(title="db password", required=False)
	
def registerGraphDB(_context, url, username=None, password=None, name=u""):
	"""
	Register an db
	"""
	factory = functools.partial(Neo4jDB, url=url, username=username, password=password)
	utility(_context, provides=graph_interfaces.IGraphDB, factory=factory, name=name)
