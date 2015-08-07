# -*- coding: utf-8 -*-

import time
import datetime
import ConfigParser
import multiprocessing
import os
from sqlalchemy.sql import and_
from sqlalchemy.orm import scoped_session, sessionmaker
from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape

from forge import DB
import forge.lib.cartesian2d as c2d
from forge.models.terrain import TerrainTile
from forge.models.tables import modelsPyramid
from forge.lib.boto_conn import getBucket, writeToS3
from forge.lib.helpers import gzipFileObject, timestamp, transformCoordinate, createBBox
from forge.lib.topology import TerrainTopology
from forge.lib.global_geodetic import GlobalGeodetic
from forge.lib.collapse_geom import processRingCoordinates
from forge.lib.logs import getLogger
from forge.lib.poolmanager import PoolManager


# Init logging
dbConfig = ConfigParser.RawConfigParser()
dbConfig.read('database.cfg')
logger = getLogger(dbConfig, __name__, suffix=timestamp())


def isInside(tile, bounds):
    if tile[0] >= bounds[0] and tile[1] >= bounds[1] and tile[2] <= bounds[2] and tile[3] <= bounds[3]:
        return True
    return False


def grid(bounds, zoomLevels, fullonly):
    geodetic = GlobalGeodetic(True)

    for tileZ in zoomLevels:
        tileMinX, tileMinY = geodetic.LonLatToTile(bounds[0], bounds[1], tileZ)
        tileMaxX, tileMaxY = geodetic.LonLatToTile(bounds[2], bounds[3], tileZ)

        for tileX in xrange(tileMinX, tileMaxX + 1):
            for tileY in xrange(tileMinY, tileMaxY + 1):
                tilebounds = geodetic.TileBounds(tileX, tileY, tileZ)
                if fullonly == 0 or isInside(tilebounds, bounds):
                    yield (tilebounds, (tileX, tileY, tileZ))

# shared counter
tilecount = multiprocessing.Value('i', 0)
skipcount = multiprocessing.Value('i', 0)


def createTile(tile):
    session = None
    pid = os.getpid()

    try:
        (bounds, tileXYZ, t0, bucket) = tile
        # Prepare models
        db = DB('database.cfg')
        session = sessionmaker()(bind=db.userEngine)

        # Get the model according to the zoom level
        model = modelsPyramid.getModelByZoom(tileXYZ[2])

        # Get the interpolated point at the 4 corners
        # 0: (minX, minY), 1: (minX, maxY), 2: (maxX, maxY), 3: (maxX, minY)
        pts = [
            (bounds[0], bounds[1], 0),
            (bounds[0], bounds[3], 0),
            (bounds[2], bounds[3], 0),
            (bounds[2], bounds[1], 0)
        ]

        def toSubQuery(x):
            return session.query(model.id, model.interpolateHeightOnPlane(pts[x])).filter(
                and_(model.bboxIntersects(createBBox(pts[x], 0.01)), model.pointIntersects(pts[x]))).subquery('p%s' % x)
        subqueries = [toSubQuery(i) for i in range(0, len(pts))]

        # Get the height of the corner points as postgis cannot properly clip
        # a polygon
        cornerPts = {}
        step = 2
        j = step
        query = session.query(*subqueries)
        for q in query:
            for i in range(0, len(q), step):
                sub = q[i:j]
                j += step
                cornerPts[sub[0]] = list(to_shape(WKBElement(sub[1])).coords)

        # Clip using the bounds
        clippedGeometry = model.bboxClippedGeom(bounds)
        query = session.query(
            model.id,
            clippedGeometry.label('clip')
        ).filter(model.bboxIntersects(bounds))

        rings = []
        for q in query:
            coords = list(to_shape(q.clip).exterior.coords)
            if q.id in cornerPts:
                pt = cornerPts[q.id][0]
                for i in range(0, len(coords)):
                    c = coords[i]
                    if c[0] == pt[0] and c[1] == pt[1]:
                        coords[i] = [c[0], c[1], pt[2]]

            try:
                rings += processRingCoordinates(coords)
            except Exception as e:
                msg = '[%s] --------- ERROR ------- occured while collapsing non triangular shapes\n' % pid
                msg += '[%s]: %s' % (pid, e)
                logger.error(msg)
                raise Exception(e)

        bucketKey = '%s/%s/%s.terrain' % (tileXYZ[2], tileXYZ[0], tileXYZ[1])
        # Skip empty tiles for now, we should instead write an empty tile to S3
        if len(rings) > 0:
            # Prepare terrain tile
            terrainTopo = TerrainTopology(ringsCoordinates=rings)
            terrainTopo.fromRingsCoordinates()
            terrainFormat = TerrainTile()
            terrainFormat.fromTerrainTopology(terrainTopo, bounds=bounds)

            # Bytes manipulation and compression
            fileObject = terrainFormat.toStringIO()
            compressedFile = gzipFileObject(fileObject)
            writeToS3(bucket, bucketKey, compressedFile, model.__tablename__)
            tend = time.time()
            tilecount.value += 1
            val = tilecount.value
            total = val + skipcount.value
            if val % 10 == 0:
                logger.info('[%s ]Last tile %s (%s rings). %s to write %s tiles. (total processed: %s)' % (pid, bucketKey, len(rings), str(datetime.timedelta(seconds=tend - t0)), val, total))

        else:
            skipcount.value += 1
            val = skipcount.value
            total = val + tilecount.value
            # One should write an empyt tile
            logger.info('[%s] Skipping %s (%s) because no features found for this tile (%s skipped from %s total)' % (pid, bucketKey, bounds, val, total))

    except Exception as e:
        logger.error(e)
        raise Exception(e)
    finally:
        if session is not None:
            session.close_all()
            db.userEngine.dispose()

    return 0


class Tiles:

    def __init__(self, tmsConfig, t0):
        self.t0 = t0

        self.minLon = float(tmsConfig.get('Extent', 'minLon'))
        self.maxLon = float(tmsConfig.get('Extent', 'maxLon'))
        self.minLat = float(tmsConfig.get('Extent', 'minLat'))
        self.maxLat = float(tmsConfig.get('Extent', 'maxLat'))
        self.fullonly = int(tmsConfig.get('Extent', 'fullonly'))

        self.tileMinZ = int(tmsConfig.get('Zooms', 'tileMinZ'))
        self.tileMaxZ = int(tmsConfig.get('Zooms', 'tileMaxZ'))

        self.tmsConfig = tmsConfig

    def __iter__(self):
        bucket = getBucket()
        zRange = range(self.tileMinZ, self.tileMaxZ + 1)
        for bounds, tileXYZ in grid((self.minLon, self.minLat, self.maxLon, self.maxLat), zRange, self.fullonly):
            yield (bounds, tileXYZ, self.t0, bucket)


class TilerManager:

    def __init__(self, configFile):
        tmsConfig = ConfigParser.RawConfigParser()
        tmsConfig.read(configFile)
        self.chunks = int(tmsConfig.get('General', 'chunks'))
        self.tmsConfig = tmsConfig

    def create(self):
        self.t0 = time.time()

        tilecount.value = 0
        skipcount.value = 0

        tiles = Tiles(self.tmsConfig, self.t0)

        pm = PoolManager()

        useChunks = self.chunks
        nbTiles = self.numOfTiles()
        tilesPerProc = int(nbTiles / pm.numOfProcesses())
        if tilesPerProc < useChunks:
            useChunks = tilesPerProc
        if useChunks < 1:
            useChunks = 1

        logger.info('Starting creation of %s tiles (%s per chunk)' % (nbTiles, useChunks))
        pm.process(tiles, createTile, useChunks)

        tend = time.time()
        logger.info('It took %s to create %s tiles (%s were skipped)' % (
            str(datetime.timedelta(seconds=tend - self.t0)), tilecount.value, skipcount.value))

    def _stats(self, withDb=True):
        self.t0 = time.time()
        total = 0

        msg = '\n'
        tiles = Tiles(self.tmsConfig, self.t0)
        geodetic = GlobalGeodetic(True)
        bounds = (tiles.minLon, tiles.minLat, tiles.maxLon, tiles.maxLat)
        zooms = range(tiles.tileMinZ, tiles.tileMaxZ + 1)

        db = DB('database.cfg')
        self.DBSession = scoped_session(sessionmaker(bind=db.userEngine))

        for i in xrange(0, len(zooms)):
            zoom = zooms[i]
            model = modelsPyramid.getModelByZoom(zoom)
            nbObjects = None
            if withDb:
                nbObjects = self.DBSession.query(model).filter(model.bboxIntersects(bounds)).count()
            tileMinX, tileMinY = geodetic.LonLatToTile(bounds[0], bounds[1], zoom)
            tileMaxX, tileMaxY = geodetic.LonLatToTile(bounds[2], bounds[3], zoom)
            # Fast approach, but might not be fully correct
            if tiles.fullonly == 1:
                tileMinX += 1
                tileMinY += 1
                tileMaxX -= 1
                tileMaxY -= 1
            tileBounds = geodetic.TileBounds(tileMinX, tileMinY, zoom)
            xCount = tileMaxX - tileMinX + 1
            yCount = tileMaxY - tileMinY + 1
            nbTiles = xCount * yCount
            total += nbTiles
            pointA = transformCoordinate('POINT(%s %s)' % (tileBounds[0], tileBounds[1]), 4326, 21781).GetPoints()[0]
            pointB = transformCoordinate('POINT(%s %s)' % (tileBounds[2], tileBounds[3]), 4326, 21781).GetPoints()[0]
            length = c2d.distance(pointA, pointB)
            if tiles.fullonly == 1:
                msg += 'WARNING: stats are approximative because fullonly is activated!\n'
            msg += 'At zoom %s:\n' % zoom
            msg += 'We expect %s tiles overall\n' % nbTiles
            msg += 'Min X is %s, Max X is %s\n' % (tileMinX, tileMaxX)
            msg += '%s columns over X\n' % xCount
            msg += 'Min Y is %s, Max Y is %s\n' % (tileMinY, tileMaxY)
            msg += '%s rows over Y\n' % yCount
            msg += '\n'
            msg += 'A tile side is around %s meters long\n' % int(round(length))
            if nbTiles > 0 and nbObjects is not None:
                msg += 'We have an average of about %s triangles per tile\n' % int(round(nbObjects / nbTiles))
            msg += '\n'

        return (total, msg)

    def numOfTiles(self):
        (total, msg) = self._stats(False)
        return total

    def stats(self):
        (total, msg) = self._stats(True)
        logger.info(msg)

    def statsNoDb(self):
        (total, msg) = self._stats(False)
        logger.info(msg)
