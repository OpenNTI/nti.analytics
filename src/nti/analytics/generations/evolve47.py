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

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.analytics import QUEUE_NAMES

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.interfaces import IRedisClient

generation = 47

logger = __import__('logging').getLogger(__name__)


def _unpickle(data):
    data = zlib.decompress(data)
    bio = BytesIO(data)
    bio.seek(0)
    result = pickle.load(bio)
    return result


def _reset(redis, name, hash_key):
    keys = redis.pipeline().delete(name) \
                .hkeys(hash_key).execute()
    if keys and keys[1]:
        redis.hdel(hash_key, *keys[1])
        return keys[1]
    return ()


def _load_library():
    library = component.queryUtility(IContentPackageLibrary)
    if library is not None:
        library.syncContentPackages()


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        _load_library()

        _redis = component.queryUtility(IRedisClient)
        for name in QUEUE_NAMES:
            # process jobs
            hash_key = name + '/hash'
            data = _redis.lrange(name, 0, -1)
            for job in (_unpickle(x) for x in data or ()):
                try:
                    job()
                except Exception:
                    logger.error("Cannot execute analytics job %s", job)
            _reset(_redis, name, hash_key)

            # reset failed 
            name += "/failed"
            hash_key = name + '/hash'
            _reset(_redis, name, hash_key)

    logger.info('Analytics evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 47 by executing all jobs in the queues 
    """
    do_evolve(context, generation)
