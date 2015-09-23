# -*- coding: utf-8 -*-

import os
import ConfigParser
from geoalchemy2 import Geometry
from sqlalchemy import event
from sqlalchemy.schema import CreateSchema
from sqlalchemy import Column, Sequence, BigInteger, Text
from sqlalchemy.ext.declarative import declarative_base

from forge.models import Vector
from forge.lib.helpers import isShapefile


Base = declarative_base()
event.listen(Base.metadata, 'before_create', CreateSchema('data'))

table_args = {'schema': 'data'}
# management to true only for postgis 1.5
WGS84Polygon = Geometry(geometry_type='POLYGON', srid=4326, dimension=3, spatial_index=True, management=True)


def modelFactory(BaseClass, tablename, shapefiles, classname):
    sequence = Sequence('id_%s_seq' % tablename, schema=table_args['schema'])

    class NewClass(BaseClass, Vector):
        __tablename__ = tablename
        __table_args__ = table_args
        __shapefiles__ = shapefiles
        id = Column(BigInteger(), sequence, nullable=False, primary_key=True)
        shapefilepath = Column('shapefilepath', Text)
        the_geom = Column('the_geom', WGS84Polygon)
    NewClass.__name__ = classname
    return NewClass


class ModelsPyramid:

    def __init__(self, dbConfigFile, tmsConfigFile):
        dbConfig = ConfigParser.RawConfigParser()
        dbConfig.read(dbConfigFile)
        self.baseDir = dbConfig.get('Data', 'baseDir')
        self.shpsBaseDir = dbConfig.get('Data', 'shapefiles').split(',')
        self.tablenames = dbConfig.get('Data', 'tablenames').split(',')
        self.modelnames = dbConfig.get('Data', 'modelnames').split(',')
        self.tmsConfigFile = tmsConfigFile

        self.models = []
        self._createModels()

    def _createModels(self):
        for i in range(0, len(self.shpsBaseDir)):
            shpBaseDir = '%s%s' % (self.baseDir, self.shpsBaseDir[i])
            if os.path.exists(shpBaseDir):
                shapefiles = ['%s%s' % (shpBaseDir, f) for f in os.listdir(shpBaseDir) if isShapefile(f)]
            else:
                shapefiles = []
            self.models.append(modelFactory(
                Base, self.tablenames[i], shapefiles, self.modelnames[i]
            ))

        self._buildModelsPyramid()

    def _buildModelsPyramid(self):
        tmsConfig = ConfigParser.RawConfigParser()
        tmsConfig.read(self.tmsConfigFile)
        self.tileMinZ = int(tmsConfig.get('Zooms', 'tileMinZ'))
        self.tileMaxZ = int(tmsConfig.get('Zooms', 'tileMaxZ'))

        self.modelsPyramid = {}
        for i in range(self.tileMinZ, self.tileMaxZ + 1):
            for j in range(0, len(self.models)):
                model = self.models[j]
                tableName = tmsConfig.get(str(i), 'tablename')
                if model.__tablename__ == tableName:
                    self.modelsPyramid[str(i)] = j
                    break

    def getModelByZoom(self, zoom):
        zoom = str(zoom)
        if zoom in self.modelsPyramid:
            return self.models[
                self.modelsPyramid[zoom]
            ]
        return None


modelsPyramid = ModelsPyramid('database.cfg', 'tms.cfg')
