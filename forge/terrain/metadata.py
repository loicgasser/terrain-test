# -*- coding: utf-8 -*-

from forge.lib.tilejson import _TileJSON


class TerrainMetadata(_TileJSON):

    def __init__(self, *args, **kwargs):

        self.gridOrigin = 'bottomLeft'
        self.tileMinZoom = kwargs.get('minzoom')
        self.tileMaxZoom = kwargs.get('maxzoom')
        self.useGlobalTiles = kwargs.get('useGlobalTiles', False)
        self.baseUrls = kwargs.get('baseUrls',
            ['//3d.geo.admin.ch/1.0.0/ch.swisstopo.terrain.3d_water/'
             'default/20151231/4326/{z}/{x}/{y}.terrain'])
        self.hasLighting = kwargs.get('hasLighting', False)
        self.hasWatermask = kwargs.get('hasWatermask', False)

        extensions = []

        if self.hasLighting:
            extensions.append('octvertexnormals')
            extensions.append('vertexnormals')
        if self.hasWatermask:
            extensions.append('watermask')

        self.available = [[] for i in range(self.tileMinZoom, self.tileMaxZoom + 1)]
        self.meta = dict(
            tilejson     = kwargs.get('tilejson', '2.1.0'),
            name         = kwargs.get('name', 'ch.swisstopo.terrain.3d'),
            description  = kwargs.get('version', '2.0.0'),
            format       = kwargs.get('format', 'quantized-mesh-1.0'),
            attribution  = kwargs.get('attribution', None),
            scheme       = kwargs.get('scheme', 'tms'),
            tiles        = kwargs.get('tiles', self.baseUrls),
            minzoom      = self.tileMinZoom,
            maxzoom      = self.tileMaxZoom,
            bounds       = kwargs.get('bounds', [-180, -90, 180, 90]),
            projection   = kwargs.get('projection', 'EPSG:4326'),
            available    = kwargs.get('available', self.available),
            version      = kwargs.get('version', '1.0.0'),
            #extensions   = extensions
        )

        self._initPyramidMetadata()
