# -*- coding: utf-8 -*-

import unittest
import os
from forge.lib.shapefile_utils import ShpToGDALFeatures


class TestShpToGDALFeatures(unittest.TestCase):

#    def setUp(self):

#    def tearDown(self):

    def testReader(self):
        curDir = os.getcwd()
        reader = ShpToGDALFeatures(shpFilePath = curDir + '/forge/data/shapefile-topo/1209-21_CH1902_LV03.shp')
        features = reader.__read__()

        # self.assertEqual(3597, len(features))
