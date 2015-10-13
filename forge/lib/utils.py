# -*- coding: utf-8 -*-

import requests
import cStringIO

from forge.lib.tiler import grid
from forge.lib.helpers import gzipFileObject
from forge.lib.boto_conn import getBucket, writeToS3


def tilePathTemplate(x, y, z):
    return '%s/%s/%s.terrain' % (z, x, y)


def loadTileContent(baseURL, key, headers):
    url = '%s%s' % (baseURL, key)
    r = requests.get(url, headers=headers)
    if r.status_code != requests.codes.ok:
        raise Exception('Failed to request %s, status code: %s' % (url, r.status_code))
    return r.content


def copyAGITiles(zooms, bounds):
    count = 0
    fullonly = 0
    headers = {'Accept': 'application/vnd.quantized-mesh;extensions=octvertexnormals-' +
        'watermask,application/octet-stream;q=0.9,*/*;q=0.01'}
    baseURL = 'http://assets.agi.com/stk-terrain/world/'
    bucket = getBucket()
    for bxyz in grid(bounds, zooms, fullonly):
        f = cStringIO.StringIO()
        tilebounds, [x, y, z] = bxyz
        bucketKey = tilePathTemplate(x, y, z)
        f.write(loadTileContent(baseURL, bucketKey, headers))
        f.seek(0)
        compressedFile = gzipFileObject(f)
        writeToS3(bucket, bucketKey, compressedFile, 'poc_watermask')
        count += 1
        if count % 20 == 0:
            print 'Copying %s...' % bucketKey
            print '%s tiles have been copied so far.' % count
