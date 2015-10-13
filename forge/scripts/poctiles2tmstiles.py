# -*- coding: utf-8 -*-

import sys
import gzip
import os
import getopt
import json
from urllib2 import urlopen
from textwrap import dedent

from forge.lib.global_geodetic import GlobalGeodetic
from forge.lib.helpers import error
from forge.terrain import TerrainTile
# from forge.terrain.topology import TerrainTopology
from forge.lib.helpers import gzipFileObject
from forge.lib.boto_conn import getBucket, writeToS3
# from forge.lib.shapefile_utils import ShpToGDALFeatures


poc_base_url = "http://ec2-54-220-242-89.eu-west-1.compute.amazonaws.com/stk-terrain/tilesets/swisseudem/tiles/"
temp_file_name = "tmp/poc.terrain"
gzip_file_name = temp_file_name + ".gzip"
tms_file_name = "tmp/tms.terrain"
shape_file_name = "tmp/shape.shp"
tms_from_shape_file_name = "tmp/tms.from.shape.terrain"


def usage():
    print(dedent('''\
        Usage: venv/bin/python forge/script/poctiles2tmstiles.py [-f <nr>|--from=<nr>] [-t <nr>|--to=<nr>] [<file>]')

        - f (from zoom level, as read from top-level layers.json
        - t (to zoom level, as read from top-level layers.json

        The <file> contains tiles to transform in the form /z/x/y

        <file> and -f/-t are mutually exclusive (can't have both at same time)

        Script will
            1) get given tile from poc url
            2) read tile with TerrainTile class (fromFile function)
            3) Write tile to our S3 bucket under given addres /z/x/y
    '''))


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'f:t:', ['from=', 'to='])
    except getopt.GetoptError as err:
        error(str(err), 2, usage=usage)

    ffrom = None
    to = None
    ffile = None

    for o, a in opts:
        if o in ('-f', '--from'):
            ffrom = a
        if o in ('-t', '--to'):
            to = a

    if ffrom is None or to is None:
        if len(args) != 1:
            error("Please specify a file.", 4, usage=usage)
        ffile = args[0]

    tiles = []

    # We have file, so we get the tiles from the file
    if ffile is not None:
        with open(ffile) as f:
            for line in f:
                line = line.rstrip()
                if len(line) > 2:
                    tiles.append(map(int, line.split('/')))

    # If we have from to, we catch layers.json from poc and use from to for levels
    if ffrom is not None and to is not None:
        req = urlopen(poc_base_url + 'layer.json')
        layers = {}
        for line in req:
            layers = json.loads(line)
        for zoom in range(int(ffrom), int(to) + 1):
            level = layers['available'][zoom][0]
            for x in range(int(level['startX']), int(level['endX']) + 1):
                for y in range(int(level['startY']), int(level['endY']) + 1):
                    tiles.append([zoom, x, y])

    bucket = getBucket()
    g = GlobalGeodetic(tmscompatible=True)
    if not os.path.isdir('tmp'):
        os.mkdir('tmp')
    for tile in tiles:
        req = None
        tilebounds = g.TileBounds(tile[1], tile[2], tile[0])
        tilestring = str(tile[0]) + "/" + str(tile[1]) + "/" + str(tile[2])
        try:
            url = poc_base_url + tilestring + ".terrain?v=2.0.0"
            req = urlopen(url)
            with open(gzip_file_name, 'wb') as fp:
                fp.write(req.read())
            ff = gzip.open(gzip_file_name)
            with open(temp_file_name, 'wb') as fp:
                fp.write(ff.read())

            ter = TerrainTile()
            ter.fromFile(temp_file_name, tilebounds[0], tilebounds[2], tilebounds[1], tilebounds[3])
            '''
            if os.path.isfile(tms_file_name):
                os.remove(tms_file_name)

            if os.path.isfile(shape_file_name):
                os.remove(shape_file_name)

            if os.path.isfile(tms_from_shape_file_name):
                os.remove(tms_from_shape_file_name)

            ter.toFile(tms_file_name)
            ter.toShapefile(shape_file_name)

            shapefile = ShpToGDALFeatures(shpFilePath=shape_file_name)
            features = shapefile.__read__()
            topology = TerrainTopology(features=features)
            topology.fromGDALFeatures()

            terFromPoc = TerrainTile()
            terFromPoc.fromFile(tms_file_name, tilebounds[0], tilebounds[2], tilebounds[1], tilebounds[3])

            terFromShape = TerrainTile()
            terFromShape.fromTerrainTopology(topology)
            terFromShape.toFile(tms_from_shape_file_name)

            # Use this to select what is written to s3
            ter2 = terFromShape
            '''
            ter2 = ter

            fileObject = ter2.toStringIO()
            compressedFile = gzipFileObject(fileObject)

            bucketKey = tilestring + '.terrain'
            print 'Uploading %s to S3' % bucketKey
            writeToS3(bucket, bucketKey, compressedFile, 'POC Tiles copy',
                contentType=ter.getContentType())

        except Exception as e:
            print "error with " + line + " " + str(e)
        finally:
            if req:
                req.close()
    return 0


if __name__ == '__main__':
    main()
