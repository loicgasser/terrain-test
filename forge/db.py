# -*- coding: utf-8 -*-

import os
import datetime
import time
import subprocess
import sys
import ConfigParser
import sqlalchemy
from geoalchemy2 import WKTElement
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from forge.lib.logs import getLogger
from forge.lib.shapefile_utils import ShpToGDALFeatures
from forge.lib.helpers import BulkInsert, timestamp, cleanup
from forge.models.tables import Base, modelsPyramid
from forge.lib.poolmanager import PoolManager


config = ConfigParser.RawConfigParser()
config.read('database.cfg')
logger = getLogger(config, __name__, suffix='db_%s' % timestamp())


# Create pickable object
class PopulateFeaturesArguments:

    def __init__(self, engineURL, modelIndex, shpFile, reproject):
        self.engineURL = engineURL
        self.modelIndex = modelIndex
        self.shpFile = shpFile
        self.reproject = reproject


def reprojectShp(shpFilePath):
    logger.info('Action reprojectShapefile(%s)' % shpFilePath)
    outDirectory = config.get('Reprojection', 'outDirectory')
    outFile = '%s%s' % (outDirectory, os.path.basename(shpFilePath))

    # If out file already exists clean it up first
    cleanup(outFile)

    command = '%(geosuiteCmd)s -calc reframe -in %(inFile)s -out %(outFile)s -pframes %(fromPFrames)s,%(toPFrames)s ' \
        '-aframes %(fromAFrames)s,%(toAFrames)s -log %(logfile)s -err %(errorfile)s' % dict(
            geosuiteCmd=config.get('Reprojection', 'geosuiteCmd'),
            inFile=shpFilePath,
            outFile=outFile,
            fromPFrames=config.get('Reprojection', 'fromPFrames'),
            toPFrames=config.get('Reprojection', 'toPFrames'),
            fromAFrames=config.get('Reprojection', 'fromAFrames'),
            toAFrames=config.get('Reprojection', 'toAFrames'),
            logfile=config.get('Reprojection', 'logfile'),
            errorfile=config.get('Reprojection', 'errorfile')
        )
    try:
        logger.info('Command: %s' % command)
        subprocess.call(command, shell=True)
    except Exception as e:
        logger.error('Could not reproject %(inFile)s into %(outFile)s: %(err)s' % dict(
            inFile=shpFilePath,
            outFile=outFile,
            err=e
        ))
        raise Exception(e)

    # As we can't detect a success from an error with the current implementation
    # We determine if the output file exists and exit if not
    if not os.path.isfile(outFile):
        logger.error('File could not be reprojected')
        logger.error('Have a look at %(logfile)s or %(errorfile)s for more information.' % dict(
            logfile=config.get('Reprojection', 'logfile'),
            errorfile=config.get('Reprojection', 'errorfile')
        ))
        raise Exception('File could not be reprojected!!')

    return outFile


def populateFeatures(args):
    pid = os.getpid()
    session = None
    shpFile = args.shpFile
    reproject = args.reproject
    keepfiles = True if config.get('Reprojection', 'keepfiles') == '1' else False

    if reproject:
        try:
            shpFile = reprojectShp(shpFile)
        except Exception as e:
            raise Exception(e)

    try:
        models = modelsPyramid.models
        engine = sqlalchemy.create_engine(args.engineURL)
        session = scoped_session(sessionmaker(bind=engine))
        model = models[args.modelIndex]

        if not os.path.exists(shpFile):
            logger.error('[%s]: Shapefile %s does not exists' % (pid, shpFile))
            sys.exit(1)

        count = 1
        shp = ShpToGDALFeatures(shpFile)
        logger.info('[%s]: Processing %s' % (pid, shpFile))
        bulk = BulkInsert(model, session, withAutoCommit=1000)
        for feature in shp.getFeatures():
            polygon = feature.GetGeometryRef()
            bulk.add(dict(
                the_geom=WKTElement(polygon.ExportToWkt(), 4326)
            ))
            count += 1
        bulk.commit()
        logger.info('[%s]: Commit %s features for %s.' % (pid, count, shpFile))
    except Exception as e:
        logger.error(e)
        raise Exception(e)
    finally:
        if session is not None:
            session.close_all()
            engine.dispose()

    if reproject:
        # Discard file after reprojection if specified in config
        if not keepfiles:
            logger.info('[%s] Removing %s...' % (pid, shpFile))
            cleanup(shpFile)

    return count


class DB:

    class Server:

        def __init__(self, config):
            self.host = config.get('Server', 'host')
            self.port = config.getint('Server', 'port')

    class Admin:

        def __init__(self, config):
            self.user = config.get('Admin', 'user')
            self.password = config.get('Admin', 'password')

    class Database:

        def __init__(self, config):
            self.name = config.get('Database', 'name')
            self.user = config.get('Database', 'user')
            self.password = config.get('Database', 'password')

    def __init__(self, configFile):

        self.serverConf = DB.Server(config)
        self.adminConf = DB.Admin(config)
        self.databaseConf = DB.Database(config)

        self.superEngine = sqlalchemy.create_engine(
            'postgresql+psycopg2://%(user)s:%(password)s@%(host)s:%(port)d/%(database)s' % dict(
                user=self.adminConf.user,
                password=self.adminConf.password,
                host=self.serverConf.host,
                port=self.serverConf.port,
                database='postgres'
            )
        )

        self.adminEngine = sqlalchemy.create_engine(
            'postgresql+psycopg2://%(user)s:%(password)s@%(host)s:%(port)d/%(database)s' % dict(
                user=self.adminConf.user,
                password=self.adminConf.password,
                host=self.serverConf.host,
                port=self.serverConf.port,
                database=self.databaseConf.name
            )
        )
        self.userEngine = sqlalchemy.create_engine(
            'postgresql+psycopg2://%(user)s:%(password)s@%(host)s:%(port)d/%(database)s' % dict(
                user=self.databaseConf.user,
                password=self.databaseConf.password,
                host=self.serverConf.host,
                port=self.serverConf.port,
                database=self.databaseConf.name,
                poolclass=NullPool
            )
        )

    @contextmanager
    def superConnection(self):
        conn = self.superEngine.connect()
        isolation = conn.connection.connection.isolation_level
        conn.connection.connection.set_isolation_level(0)
        yield conn
        conn.connection.connection.set_isolation_level(isolation)
        conn.close()

    @contextmanager
    def adminConnection(self):
        conn = self.adminEngine.connect()
        isolation = conn.connection.connection.isolation_level
        conn.connection.connection.set_isolation_level(0)
        yield conn
        conn.connection.connection.set_isolation_level(isolation)
        conn.close()

    @contextmanager
    def userConnection(self):
        conn = self.userEngine.connect()
        yield conn
        conn.close()

    def createUser(self):
        logger.info('Action: createUser()')
        with self.superConnection() as conn:
            try:
                conn.execute(
                    "CREATE ROLE %(role)s WITH NOSUPERUSER INHERIT LOGIN ENCRYPTED PASSWORD '%(password)s'" % dict(
                        role=self.databaseConf.user,
                        password=self.databaseConf.password
                    )
                )
            except ProgrammingError as e:
                logger.error('Could not create user %(role)s: %(err)s' % dict(
                    role=self.databaseConf.user,
                    err=str(e)
                ))

    def createDatabase(self):
        logger.info('Action: createDatabase()')
        with self.superConnection() as conn:
            try:
                conn.execute(
                    "CREATE DATABASE %(name)s WITH OWNER %(role)s ENCODING 'UTF8' TEMPLATE template_postgis" % dict(
                        name=self.databaseConf.name,
                        role=self.databaseConf.user
                    )
                )
            except ProgrammingError as e:
                logger.error('Could not create database %(name)s with owner %(role)s: %(err)s' % dict(
                    name=self.databaseConf.name,
                    role=self.databaseConf.user,
                    err=str(e)
                ))

        with self.adminConnection() as conn:
            try:
                conn.execute("""
                    ALTER SCHEMA public OWNER TO %(role)s;
                    ALTER TABLE public.spatial_ref_sys OWNER TO %(role)s;
                    ALTER TABLE public.geometry_columns OWNER TO %(role)s
                """ % dict(
                    role=self.databaseConf.user
                )
                )
            except ProgrammingError as e:
                logger.error('Could not create database %(name)s with owner %(role)s: %(err)s' % dict(
                    name=self.databaseConf.name,
                    role=self.databaseConf.user,
                    err=str(e)
                ))

    def setupDatabase(self):
        logger.info('Action: setupDatabase()')
        try:
            Base.metadata.create_all(self.userEngine)
        except ProgrammingError as e:
            logger.warning('Could not setup database on %(name)s: %(err)s' % dict(
                name=self.databaseConf.name,
                err=str(e)
            ))

    def setupFunctions(self):
        logger.info('Action: setupFunctions()')

        os.environ['PGPASSWORD'] = self.databaseConf.password
        baseDir = 'forge/sql/'

        for fileName in os.listdir('forge/sql/'):
            if fileName != 'legacy.sql':
                command = 'psql -U %(user)s -d %(dbname)s -a -f %(baseDir)s%(fileName)s' % dict(
                    user=self.databaseConf.user,
                    dbname=self.databaseConf.name,
                    baseDir=baseDir,
                    fileName=fileName
                )
                try:
                    subprocess.call(command, shell=True)
                except Exception as e:
                    logger.error('Could not add custom functions %s to the database: %(err)s' % dict(
                        fileName=fileName,
                        err=str(e)
                    ))
            else:
                with self.adminConnection() as conn:
                    pgVersion = conn.execute("Select postgis_version();").fetchone()[0]
                    if pgVersion.startswith("2."):
                        logger.info('Action: setupFunctions()->legacy.sql')
                        os.environ['PGPASSWORD'] = self.adminConf.password
                        command = 'psql --quiet -h %(host)s -U %(user)s -d %(dbname)s -f %(baseDir)s%(fileName)s' % dict(
                            host=self.serverConf.host,
                            user=self.adminConf.user,
                            dbname=self.databaseConf.name,
                            baseDir=baseDir,
                            fileName=fileName
                        )
                        try:
                            subprocess.call(command, shell=True)
                        except Exception as e:
                            logger.error('Could not install postgis 2.1 legacy functions to the database: %(err)s' % dict(
                                err=str(e)
                            ))

        del os.environ['PGPASSWORD']

    def populateTables(self):
        logger.info('Action: populateTables()')

        reproject = config.get('Reprojection', 'reproject')
        tstart = time.time()
        models = modelsPyramid.models
        featuresArgs = []
        for i in range(0, len(models)):
            model = models[i]
            for shp in model.__shapefiles__:
                featuresArgs.append(PopulateFeaturesArguments(
                    self.userEngine.url,
                    i,
                    shp,
                    True if reproject == '1' else False
                ))

        pm = PoolManager()

        pm.process(featuresArgs, populateFeatures, 1)

        tend = time.time()
        logger.info('All tables have been created. It took %s' % str(datetime.timedelta(seconds=tend - tstart)))

    def dropDatabase(self):
        logger.info('Action: dropDatabase()')
        with self.superConnection() as conn:
            try:
                conn.execute(
                    "DROP DATABASE %(name)s" % dict(
                        name=self.databaseConf.name
                    )
                )
            except ProgrammingError as e:
                logger.error('Could not drop database %(name)s: %(err)s' % dict(
                    name=self.databaseConf.name,
                    err=str(e)
                ))

    def dropUser(self):
        logger.info('Action: dropUser()')
        with self.superConnection() as conn:
            try:
                conn.execute(
                    "DROP ROLE %(role)s" % dict(
                        role=self.databaseConf.user
                    )
                )
            except ProgrammingError as e:
                logger.error('Could not drop user %(role)s: %(err)s' % dict(
                    role=self.databaseConf.user,
                    err=str(e)
                ))

    def create(self):
        logger.info('Action: create()')
        self.createUser()
        self.createDatabase()
        self.setupDatabase()
        self.setupFunctions()

    def importshp(self):
        self.populateTables()

    def destroy(self):
        logger.info('Action: destroy()')
        self.dropDatabase()
        self.dropUser()
