# -*- coding: utf-8 -*-

import unittest
import os
from forge.terrain import TerrainTile
from forge.lib.global_geodetic import GlobalGeodetic


class TestTerrainTile(unittest.TestCase):

    def setUp(self):
        self.tmpfile = '.tmp/temp.terrain'
        self.tmpfile2 = '.tmp/temp2.terrain'

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)
        if os.path.exists(self.tmpfile2):
            os.remove(self.tmpfile2)

    def testReaderWriter(self):
        '''
        Circle jerk testing.
        We read the file with our reader
        We write this data with our writer to a temporary file
        We read this temporary file
        We compare the results
        '''
        ter = TerrainTile()
        # ter.fromFile('forge/data/quantized-mesh/0.terrain', 7.80938, 7.81773, 46.30261, 46.3079)
        # ter.fromFile('forge/data/quantized-mesh/raron.flat.1.terrain', 7.80938, 7.81773, 46.30261, 46.30790)
        ter.fromFile('forge/data/quantized-mesh/goms.mountains.1.terrain', 7.80938, 7.81773, 46.30261, 46.30799)
        ter.toFile(self.tmpfile)
        ter2 = TerrainTile()
        ter2.fromFile(self.tmpfile, 7.80938, 7.81773, 46.30261, 46.30799)

        # check headers
        self.failUnless(len(ter.header) > 0)
        self.assertEqual(len(ter.header), len(ter2.header))
        self.assertEqual(len(ter.header), len(TerrainTile.quantizedMeshHeader))
        for k, v in ter.header.iteritems():
            self.assertEqual(v, ter2.header[k], 'For k = ' + k)

        # check vertices
        self.failUnless(len(ter.u) > 0)
        self.failUnless(len(ter.v) > 0)
        self.failUnless(len(ter.h) > 0)
        self.assertEqual(len(ter.u), len(ter2.u))
        self.assertEqual(len(ter.v), len(ter2.v))
        self.assertEqual(len(ter.h), len(ter2.h))
        for i, v in enumerate(ter.u):
            self.assertEqual(v, ter2.u[i])
        for i, v in enumerate(ter.v):
            self.assertEqual(v, ter2.v[i])
        for i, v in enumerate(ter.h):
            self.assertEqual(v, ter2.h[i])

        # check indices
        self.failUnless(len(ter.indices) > 0)
        self.assertEqual(len(ter.indices), len(ter2.indices))
        for i, v in enumerate(ter.indices):
            self.assertEqual(v, ter2.indices[i], i)

        # check edges
        self.failUnless(len(ter.westI) > 0)
        self.assertEqual(len(ter.westI), len(ter2.westI))
        for i, v in enumerate(ter.westI):
            self.assertEqual(v, ter2.westI[i], i)

        self.failUnless(len(ter.southI) > 0)
        self.assertEqual(len(ter.southI), len(ter2.southI))
        for i, v in enumerate(ter.southI):
            self.assertEqual(v, ter2.southI[i], i)

        self.failUnless(len(ter.eastI) > 0)
        self.assertEqual(len(ter.eastI), len(ter2.eastI))
        for i, v in enumerate(ter.eastI):
            self.assertEqual(v, ter2.eastI[i], i)

        self.failUnless(len(ter.northI) > 0)
        self.assertEqual(len(ter.northI), len(ter2.northI))
        for i, v in enumerate(ter.northI):
            self.assertEqual(v, ter2.northI[i], i)

    def testExtensionsReader(self):
        z = 10
        y = 1563
        x = 590
        geodetic = GlobalGeodetic(True)

        ter = TerrainTile()
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
        ter.fromFile('forge/data/quantized-mesh/%s_%s_%s.terrain' % (z, y, x),
            minx, miny, maxx, maxy, hasLighting=True, hasWatermask=True)

        # check indices
        self.failUnless(len(ter.indices) > 0)

        # check edges
        self.failUnless(len(ter.westI) > 0)
        self.failUnless(len(ter.southI) > 0)
        self.failUnless(len(ter.eastI) > 0)
        self.failUnless(len(ter.northI) > 0)

        # check extensions
        self.assertEqual(len(ter.watermask), 1)
        self.assertEqual(len(ter.watermask[0]), 1)
        # Water only -> 255
        self.assertEqual(ter.watermask[0][0], 255)
        ter.toFile(self.tmpfile2)

        ter2 = TerrainTile()
        ter2.fromFile(self.tmpfile2,
            minx, miny, maxx, maxy, hasLighting=True, hasWatermask=True)

        self.assertEqual(len(ter.watermask), len(ter2.watermask))
        self.assertEqual(len(ter.watermask[0]), len(ter2.watermask[0]))

        sign = lambda a: 1 if a > 0 else -1 if a < 0 else 0
        for i in range(0, len(ter.vLight)):
            for j in range(0, 3):
                # We cannot have an exact equality with successive oct encoding and decoding
                # Thus we only check the sign
                self.assertEqual(sign(ter.vLight[i][j]), sign(ter2.vLight[i][j]))
