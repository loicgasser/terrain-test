# -*- coding: utf-8 -*-

import re
from osgeo import ogr


class ShpToGDALFeatures(object):

    def __init__(self, shpFilePath=None):
        if shpFilePath is None:
            raise Exception('No shapefile path provided')
        if re.search(r'(\.shp)$', shpFilePath) is None:
            raise TypeError('Only shapefiles are supported. Provided path %s' % shpFilePath)
        self.shpFilePath = shpFilePath
        self.drvName = 'ESRI Shapefile'
        self.drv = ogr.GetDriverByName(self.drvName)

    # Returns a list of GDAL Features
    def __read__(self):
        dataSource = self._getDatasource()
        # 0 refers to read-only
        layer = dataSource.GetLayer()
        print 'dast ist ' + str(layer.GetSpatialRef())
        d
        features = [feature for feature in layer]
        if len(features) == 0:
            return features
            # raise Exception('Empty shapefile')

        geometryType = features[0].GetGeometryRef().GetGeometryName()
        if geometryType != 'POLYGON':
            raise TypeError('Unsupported input geometry type: %s' % geometryType)
        return features

    def getFeatures(self):
        dataSource = self._getDatasource()
        layer = dataSource.GetLayer()
        for feature in layer:
            yield feature

    def _getDatasource(self):
        dataSource = self.drv.Open(self.shpFilePath, 0)
        if dataSource is None:
            raise IOError('Could not open %s' % self.shpFilePath)
        return dataSource
