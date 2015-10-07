# -*- coding: utf-8 -*-

import requests
import cStringIO
import shutil

from forge.lib.tiler import grid
from forge.lib.boto_conn import getBucket, writeToS3


def tilePathTemplate(x, y, z):
    return '%s/%s/%s.terrain' % (z, x, y)


def loadTileContent(baseURL, key):
    url = '%s%s' % (baseURL, key)
    r = requests.get(url, headers={'Accept': 'application/vnd.quantized-mesh;extensions=octvertexnormals'}, stream=True)
    if r.status_code != requests.codes.ok:
        raise Exception('Failed to request %s, status code: %s' % (url, r.status_code))
    return r.raw


def copyAGITiles(zooms, bounds):
    count = 0
    fullonly = 0
    baseURL = 'http://assets.agi.com/stk-terrain/world/'
    bucket = getBucket()
    for bxyz in grid(bounds, zooms, fullonly):
        f = cStringIO.StringIO()
        tilebounds, [x, y, z] = bxyz
        bucketKey = tilePathTemplate(x, y, z)
        shutil.copyfileobj(loadTileContent(baseURL, bucketKey), f)
        f.seek(0)
        writeToS3(bucket, bucketKey, f, 'poc_light')
        count += 1
        if count % 20 == 0:
            print 'Copying %s...' % bucketKey
            print '%s tiles have been copied so far.' % count
