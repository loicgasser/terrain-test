# -*- coding: utf-8 -*-

import os
import datetime
import time
import subprocess
import multiprocessing
import sys
import ConfigParser
import sqlalchemy
import signal
from geoalchemy2 import WKTElement
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from forge.lib.logs import getLogger
from forge.lib.shapefile_utils import ShpToGDALFeatures
from forge.lib.helpers import BulkInsert, timestamp
from forge.models.tables import Base, models


config = ConfigParser.RawConfigParser()
config.read('database.cfg')
logger = getLogger(config, __name__, suffix='db_%s' % timestamp())


# Create pickable object
class PopulateFeaturesArguments:

    def __init__(self, engineURL, modelIndex, shpFile, autotransform):
        self.engineURL = engineURL
        self.modelIndex = modelIndex
        self.shpFile = shpFile
        self.autoTransform = autotransform


def populateFeatures(args):
    pid = os.getpid()
    session = None
    try:
        engine = sqlalchemy.create_engine(args.engineURL)
        session = scoped_session(sessionmaker(bind=engine))
        model = models[args.modelIndex]
        shpFile = args.shpFile

        if not os.path.exists(shpFile):
            logger.error('[%s]: Shapefile %s does not exists' % (pid, shpFile))
            sys.exit(1)

        # When autotransform is enabled, we try to detect crs and transform
        # it to wgs84 using ogr2ogr cmdline tool
        # if args.autoTransform > 0:

        count = 1
        shp = ShpToGDALFeatures(shpFile)
        logger.info('[%s]: Processing %s' % (pid, shpFile))
        bulk = BulkInsert(model, session, withAutoCommit=1000)
        for feature in shp.getFeatures():
            polygon = feature.GetGeometryRef()
            # TODO Use WKBelement directly instead
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
        config = ConfigParser.RawConfigParser()
        config.read(configFile)

        self.autoTransform = config.get('Data', 'autotransform')

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
        command = 'psql -U %(user)s -d %(dbname)s -a -f forge/sql/_interpolate_height_on_plane.sql' % dict(
            user=self.databaseConf.user,
            dbname=self.databaseConf.name
        )
        try:
            subprocess.call(command, shell=True)
        except Exception as e:
            logger.error('Could not add custom functions to the database: %(err)s' % dict(
                err=str(e)
            ))
        del os.environ['PGPASSWORD']

        with self.adminConnection() as conn:
            pgVersion = conn.execute("Select postgis_version();").fetchone()[0]
            if pgVersion.startswith("2."):
                logger.info('Action: setupFunctions()->legacy.sql')
                os.environ['PGPASSWORD'] = self.adminConf.password
                command = 'psql --quiet -h %(host)s -U %(user)s -d %(dbname)s -f forge/sql/legacy.sql' % dict(
                    host=self.serverConf.host,
                    user=self.adminConf.user,
                    dbname=self.databaseConf.name
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
        tstart = time.time()
        featuresArgs = []
        for i in range(0, len(models)):
            model = models[i]
            for shp in model.__shapefiles__:
                featuresArgs.append(PopulateFeaturesArguments(
                    self.userEngine.url,
                    i,
                    shp,
                    self.autoTransform
                ))

        def init_worker():
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        pool = multiprocessing.Pool(multiprocessing.cpu_count(), init_worker)
        async = pool.map_async(populateFeatures, iterable=featuresArgs)
        closed = False

        try:
            while not async.ready():
                time.sleep(3)
        except KeyboardInterrupt:
            closed = True
            pool.terminate()
            logger.info('Keyboard interupt recieved')

        if not closed:
            pool.close()

        try:
            pool.join()
            pool.terminate()
        except Exception as e:
            for i in reversed(range(len(pool._pool))):
                p = pool._pool[i]
                if p.exitcode is None:
                    p.terminate()
                del pool._pool[i]
            logger.error('An error occured while populating the tables with shapefiles.')
            logger.error(e)
            raise Exception(e)

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
