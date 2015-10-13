# -*- coding: utf-8 -*-

import os
import time
import datetime
from forge.terrain import TerrainTile
from forge.terrain.topology import TerrainTopology
from forge.lib.shapefile_utils import ShpToGDALFeatures
from forge.lib.helpers import gzipFileObject
from forge.lib.boto_conn import getBucket, writeToS3


basePath = '/var/local/cartoweb/tmp/3dpoc/swissalti3d/Interlaken_Pyr17/'
extension = '.terrain'

i = 0
t0 = time.time()
getShapefiles = lambda x: x.endswith('.shp')
shapefilesNames = filter(getShapefiles, os.listdir(basePath))
bucket = getBucket()

for f in shapefilesNames:
    filePathSource = basePath + f
    shapefile = ShpToGDALFeatures(shpFilePath=filePathSource)
    features = shapefile.__read__()

    terrainTopo = TerrainTopology(features=features)
    terrainTopo.fromGDALFeatures()
    terrainFormat = TerrainTile()
    terrainFormat.fromTerrainTopology(terrainTopo)

    fileObject = terrainFormat.toStringIO()
    compressedFile = gzipFileObject(fileObject)

    # Hardcoded scheme because we don't have any separators in the names
    # for now
    keyPath = f[1:3] + '/' + f[3:9] + '/' + f[9:14] + extension
    print 'Writing %s to S3' % keyPath
    writeToS3(bucket, keyPath, compressedFile, basePath,
        contentType=terrainFormat.getContentType())
    i += 1
    t1 = time.time()
    ti = t1 - t0
    print 'It took %s secs to write %s/%s tiles' % (str(datetime.timedelta(seconds=ti)), i, len(shapefilesNames))
