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

from forge.models.tables import modelsPyramid, Lakes
from forge.lib.logs import getLogger
from forge.lib.shapefile_utils import ShpToGDALFeatures
from forge.lib.helpers import BulkInsert, timestamp, cleanup
from forge.lib.poolmanager import PoolManager


loggingConfig = ConfigParser.RawConfigParser()
loggingConfig.read('logging.cfg')
logger = getLogger(loggingConfig, __name__, suffix='db_%s' % timestamp())


# Create pickable object
class PopulateFeaturesArguments(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def reprojectShp(shpFilePath, args):
    logger.info('Action reprojectShapefile(%s)' % shpFilePath)
    outDirectory = args.outDirectory
    outFile = '%s%s' % (outDirectory, os.path.basename(shpFilePath))

    try:
        # If out file already exists clean it up first
        cleanup(outFile)

        command = 'mono %(geosuiteCmd)s -calc reframe -in %(inFile)s -out %(outFile)s -pframes %(fromPFrames)s,%(toPFrames)s ' \
            '-aframes %(fromAFrames)s,%(toAFrames)s -log %(logfile)s -err %(errorfile)s' % dict(
                geosuiteCmd = args.geosuiteCmd,
                inFile      = args.shpFile,
                outFile     = outFile,
                fromPFrames = args.fromPFrames,
                toPFrames   = args.toPFrames,
                fromAFrames = args.fromAFrames,
                toAFrames   = args.toAFrames,
                logfile     = args.logfile,
                errorfile   = args.errorfile
            )
        logger.info('Command: %s' % command)
        subprocess.call(command, shell=True)
    except Exception as e:
        logger.error('Could not reproject %(inFile)s into %(outFile)s: %(err)s' % dict(
            inFile  = shpFilePath,
            outFile = outFile,
            err     = e
        ), exc_info=True)
        raise Exception(e)

    # TODO new version has error codes this can now be changed
    # As we can't detect a success from an error with the current implementation
    # We determine if the output file exists and exit if not
    if not os.path.isfile(outFile):
        logger.error('File could not be reprojected')
        logger.error('Have a look at %(logfile)s or %(errorfile)s for more information.' % dict(
            logfile   = args.logfile,
            errorfile = args.errorfile
        ))
        raise Exception('File could not be reprojected!!')

    return outFile


def populateFeatures(args):
    pid = os.getpid()
    session = None
    shpFile = args.shpFile
    reproject = args.reproject
    keepfiles = args.keepfiles

    if reproject:
        try:
            shpFile = reprojectShp(shpFile, args)
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
            # add shapefile path to dict
            # self.shpFilePath
            bulk.add(dict(
                the_geom = WKTElement(polygon.ExportToWkt(), 4326),
                shapefilepath=shpFile
            ))
            count += 1
        bulk.commit()
        logger.info('[%s]: Commit %s features for %s.' % (pid, count, shpFile))
    except Exception as e:
        logger.error(e, exc_info=True)
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

        if isinstance(configFile, str):
            config = ConfigParser.RawConfigParser()
            config.read(configFile)
            self.config = config
        else:
            config = configFile

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

    @contextmanager
    def userSession(self):
        engine = sqlalchemy.create_engine(self.userEngine.url)
        session = scoped_session(sessionmaker(bind=engine))
        yield session
        session.close()

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
                ), exc_info=True)

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
                ), exc_info=True)

        with self.adminConnection() as conn:
            try:
                conn.execute("""
                    ALTER SCHEMA public OWNER TO %(role)s;
                    ALTER TABLE public.spatial_ref_sys OWNER TO %(role)s;
                    ALTER TABLE public.geometry_columns OWNER TO %(role)s
                """ % dict(
                    role=self.databaseConf.user
                ))
            except ProgrammingError as e:
                logger.error('Could not create database %(name)s with owner %(role)s: %(err)s' % dict(
                    name=self.databaseConf.name,
                    role=self.databaseConf.user,
                    err=str(e)
                ), exc_info=True)

    def setupDatabase(self):
        logger.info('Action: setupDatabase()')
        try:
            for model in modelsPyramid.models:
                model.__table__.create(self.userEngine, checkfirst=True)
            Lakes.__table__.create(self.userEngine, checkfirst=True)
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
                    ), exc_info=True)
                    logger.error(command)
            else:
                with self.adminConnection() as conn:
                    pgVersion = conn.execute("Select postgis_version();").fetchone()[0]
                    if pgVersion.startswith("2."):
                        logger.info('Action: setupFunctions() -> legacy.sql')
                        command = 'psql --quiet -h %(host)s -U %(user)s -d %(dbname)s -f %(baseDir)s%(fileName)s' % dict(
                            host=self.serverConf.host,
                            user=self.databaseConf.user,
                            dbname=self.databaseConf.name,
                            baseDir=baseDir,
                            fileName=fileName
                        )
                        try:
                            subprocess.call(command, shell=True)
                        except Exception as e:
                            logger.error('Could not install postgis 2.1 legacy functions to the database: %(err)s' % dict(
                                err=str(e)
                            ), exc_info=True)
                            logger.error(command)

        del os.environ['PGPASSWORD']

    def populateTables(self):
        logger.info('Action: populateTables()')

        reproject    = self.config.get('Reprojection', 'reproject')
        keepfiles    = self.config.get('Reprojection', 'keepfiles')
        outDirectory = self.config.get('Reprojection', 'outDirectory')
        geosuiteCmd  = self.config.get('Reprojection', 'geosuiteCmd')
        fromPFrames  = self.config.get('Reprojection', 'fromPFrames')
        toPFrames    = self.config.get('Reprojection', 'toPFrames')
        fromAFrames  = self.config.get('Reprojection', 'fromAFrames')
        toAFrames    = self.config.get('Reprojection', 'toAFrames')
        logfile      = self.config.get('Reprojection', 'logfile')
        errorfile    = self.config.get('Reprojection', 'errorfile')

        if not os.path.exists(outDirectory):
            raise OSError('%s does not exist' % outDirectory)
        if not os.path.exists(geosuiteCmd):
            raise OSError('%s does not exist' % geosuiteCmd)

        tstart = time.time()
        models = modelsPyramid.models
        featuresArgs = []
        for i in range(0, len(models)):
            model = models[i]
            for shp in model.__shapefiles__:

                featuresArgs.append(PopulateFeaturesArguments(
                    engineURL    = self.userEngine.url,
                    modelIndex   = i,
                    shpFile      = shp,
                    reproject    = True if reproject == '1' else False,
                    keepfiles    = True if keepfiles == '1' else False,
                    outDirectory = outDirectory,
                    geosuiteCmd  = geosuiteCmd,
                    fromPFrames  = fromPFrames,
                    toPFrames    = toPFrames,
                    fromAFrames  = fromAFrames,
                    toAFrames    = toAFrames,
                    logfile      = logfile,
                    errorfile    = errorfile
                ))

        pm = PoolManager(logger=logger)

        pm.process(featuresArgs, populateFeatures, 1)

        tend = time.time()
        logger.info('All tables have been created. It took %s' % str(datetime.timedelta(seconds=tend - tstart)))

    def populateLakes(self):
        self.setupDatabase()
        logger.info('Action: populateLakes()')

        # For now we never reproject lakes
        engine = sqlalchemy.create_engine(self.userEngine.url)
        session = scoped_session(sessionmaker(bind=engine))
        shpFile = self.config.get('Data', 'lakes')

        if not os.path.exists(shpFile):
            logger.error('Shapefile %s does not exists' % (shpFile))
            sys.exit(1)

        count = 1
        shp = ShpToGDALFeatures(shpFile)
        logger.info('Processing %s' % (shpFile))
        bulk = BulkInsert(Lakes, session, withAutoCommit=1000)

        for feature in shp.getFeatures():
            polygon = feature.GetGeometryRef()
            # Force 2D for lakes
            polygon.FlattenTo2D()
            # add shapefile path to dict
            # self.shpFilePath
            bulk.add(dict(
                the_geom = WKTElement(polygon.ExportToWkt(), 4326)
            ))
            count += 1
        bulk.commit()
        logger.info('Commit %s features for %s.' % (count, shpFile))

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
                ), exc_info=True)

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
                ), exc_info=True)

    def create(self):
        logger.info('Action: create()')
        self.createUser()
        self.createDB()

    def createDB(self):
        logger.info('Action: createDB()')
        self.createDatabase()
        self.setupDatabase()
        self.setupFunctions()

    def populate(self):
        logger.info('Action: populate()')
        # Create missing tables in case new ones were added
        self.setupDatabase()
        self.populateTables()

    def destroy(self):
        logger.info('Action: destroy()')
        self.dropDatabase()
        self.dropUser()

    def console(self):
        logger.info('Action: console()')
        os.environ['PGPASSWORD'] = self.databaseConf.password
        cmdline = 'psql -h %(host)s -p %(port)d -U %(user)s %(name)s' % dict(
            host    = self.serverConf.host,
            port    = self.serverConf.port,
            user    = self.databaseConf.user,
            name    = self.databaseConf.name
        )
        cmd = cmdline.split()
        os.spawnvpe(os.P_WAIT, cmd[0], cmd, os.environ)
        del os.environ['PGPASSWORD']
