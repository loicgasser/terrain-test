# -*- coding: utf-8 -*-

from forge.terrain import TerrainTile
from forge.lib.global_geodetic import GlobalGeodetic

geodetic = GlobalGeodetic(True)
bounds = geodetic.TileBounds(0, 0, 0)
ter = TerrainTile(lightning=True)
# ter.fromFile('forge/data/quantized-mesh/0.terrain')
ter.fromFile('forge/data/quantized-mesh/0_0_0_light.terrain', bounds[0], bounds[2], bounds[1], bounds[3])
# ter.fromFile('forge/data/quantized-mesh/goms.mountains.1.terrain')
ter.computeVerticesCoordinates(epsg=21781)
print ter
print ter.lightning
