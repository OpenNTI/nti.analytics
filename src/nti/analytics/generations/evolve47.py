#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: evolve7.py 124460 2017-11-30 23:21:14Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=W0212,W0621,W0703

import zlib
import pickle
from io import BytesIO

from zope import component
from zope import interface

from zope.component.hooks import getSite
from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.analytics import QUEUE_NAMES

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver
from nti.dataserver.interfaces import IRedisClient

generation = 47

logger = __import__('logging').getLogger(__name__)


def _unpickle(data):
    data = zlib.decompress(data)
    bio = BytesIO(data)
    bio.seek(0)
    result = pickle.load(bio)
    return result


def _reset(redis_client, name, hash_key):
    keys = redis_client.pipeline().delete(name) \
                       .hkeys(hash_key).execute()
    if keys and keys[1]:
        redis_client.hdel(hash_key, *keys[1])
        return keys[1]
    return ()


def _load_library():
    library = component.queryUtility(IContentPackageLibrary)
    if library is not None:
        library.syncContentPackages()


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None
    root_folder = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']
    redis_client = component.getUtility(IRedisClient)

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        # set root folder
        mock_ds.root_folder = getSite().__parent__
        
        _load_library()

        for name in QUEUE_NAMES:
            # process jobs
            hash_key = name + '/hash'
            data = redis_client.lrange(name, 0, -1)
            for job in (_unpickle(x) for x in data or ()):
                try:
                    job()
                except Exception:
                    logger.error("Cannot execute analytics job %s", job)
            _reset(redis_client, name, hash_key)

            # reset failed 
            name += "/failed"
            hash_key = name + '/hash'
            _reset(redis_client, name, hash_key)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Analytics evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 47 by executing all jobs in the queues 
    """
    do_evolve(context, generation)
