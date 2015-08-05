# -*- coding: utf-8 -*-


class TerrainMetadata:

    availableRectangle = dict(
        startX = 0,
        startY = 0,
        endX   = 0,
        endY   = 0
    )

    def __init__(self, *args, **kwargs):

        self.bounds      = kwargs.get('bounds')
        self.tileMinZoom = kwargs.get('minzoom')
        self.tileMaxZoom = kwargs.get('maxzoom')

        # For each zoom level defines a list of availableRectangle(s), where index=0 refers to
        # the tileMinZoom. Note that the length of this list is 1 if all the tiles exist for a given extent
        self.available = [[] for i in range(self.tileMinZoom, self.tileMaxZoom + 1)]
        self.meta = dict(
            tilejson    = kwargs.get('tilejson', '2.1.0'),
            name        = kwargs.get('name', None),
            description = kwargs.get('version', '2.0.0'),
            format      = kwargs.get('format', 'quantized-mesh-1.0'),
            attribution = kwargs.get('attribution', None),
            scheme      = kwargs.get('scheme', 'tms'),
            tiles       = list(kwargs.get('tiles', '{z}/{x}/{y}.terrain?v={version}')),
            minzoom     = minZoom,
            maxzoom     = maxZoom,
            bounds      = kwargs.get('bounds', [-180, -90, 180, 90]),
            projection  = kwargs.get('projection', 'EPSG:4326'),
            available   = kwargs.get('available', self.available)
        )

        


    def _initMeta(self):
        # Meta is used to generate the available dict
        # when toJson method is called
        # It keeps track of the starting and ending tiles
        # and the missing tiles in between
        self.meta = {}
        # Assume the whole extent is available
        for zoom in range(self.tileMinZoom, self.tileMaxZoom + 1):
            tileMinX, tileMinY = geodetic.LonLatToTile(bounds[0], bounds[1], zoom)
            tileMaxX, tileMaxY = geodetic.LonLatToTile(bounds[2], bounds[3], zoom)
            self.meta[zoom] = dict(
                x = [tileMinX, tileMaxX], 
                y = [tileMinY, tileMaxY]
            )


    # Called when a tile is missing
    # Used while generating the tiles
    def insertMissingTile(self, tileX, tileY, tileZ):
        raise NotImplemented()


    # Called when listing the tiles from S3
    def addTile(self, tileX, tileY, tileZ):
        raise NotImplemented()


    def toJSON(self):
        raise NotImplemented()
