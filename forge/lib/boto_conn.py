# -*- coding: utf-8 -*-

import sys
import time
import datetime
import logging
import multiprocessing
import ConfigParser
from forge.lib.helpers import timestamp
from boto import connect_s3
from forge.lib.logs import getLogger
from boto.s3.key import Key
import boto.sqs

from forge.lib.poolmanager import PoolManager

logging.getLogger('boto').setLevel(logging.CRITICAL)

tmsConfig = ConfigParser.RawConfigParser()
tmsConfig.read('tms.cfg')
bucketName = tmsConfig.get('General', 'bucketName')
profileName = tmsConfig.get('General', 'profileName')
basePath = tmsConfig.get('General', 'bucketpath')

# Init logging
loggingConfig = ConfigParser.RawConfigParser()
loggingConfig.read('logging.cfg')
log = getLogger(loggingConfig, __name__, suffix=timestamp())


def _getS3Conn():
    try:
        conn = connect_s3(profile_name=profileName)
    except Exception as e:
        raise Exception('S3: Error during connection %s' % e)
    return conn


connS3 = _getS3Conn()


def getBucket():
    try:
        bucket = connS3.get_bucket(bucketName)
    except Exception as e:
        raise Exception('Error during connection %s' % e)
    return bucket


def writeToS3(b, path, content, origin, contentType='application/octet-stream', contentEnc='gzip'):
    headers = {'Content-Type': contentType}
    k = Key(b)
    k.key = basePath + path
    k.set_metadata('IWI_Origin', origin)
    headers['Content-Encoding'] = contentEnc
    headers['Access-Control-Allow-Origin'] = '*'
    k.set_contents_from_file(content, headers=headers)

copycount = multiprocessing.Value('i', 0)


def copyKey(args):
    (keyname, prefix, toPrefix, t0) = args
    try:
        bucket = getBucket()
        key = bucket.lookup(prefix + keyname)
        key.copy(bucket.name, toPrefix + keyname)
        copycount.value += 1
        val = copycount.value
        if val % 100 == 0:
            log.info('Created %s copies in %s.' % (val, str(datetime.timedelta(seconds=time.time() - t0))))
            log.info('%s was copied to %s' % (prefix + keyname, toPrefix + keyname))
    except Exception as e:
        log.info('Caught an exception when copying %s exception: %s' % (keyname, str(e)))


class S3KeyIterator:

    def __init__(self, prefix, toPrefix, t0):
        self.bucketlist = getBucket().list(prefix=prefix)
        self.prefix = prefix
        self.toPrefix = toPrefix
        self.t0 = t0

    def __iter__(self):
        for entry in self.bucketlist:
            keyname = entry.name.split(self.prefix)[1]
            yield (keyname, self.prefix, self.toPrefix, self.t0)


def copyKeys(fromPrefix, toPrefix, zooms):
    t0 = time.time()
    copycount.value = 0
    for zoom in zooms:
        log.info('doing zoom ' + str(zoom))
        t0zoom = time.time()
        keys = S3KeyIterator(fromPrefix + str(zoom) + '/', toPrefix + str(zoom) + '/', t0)

        pm = PoolManager(log)

        pm.process(keys, copyKey, 50)

        log.info(
            'It took %s to copy this zoomlevel (total %s)' %
            (str(
                datetime.timedelta(
                    seconds=time.time() -
                    t0zoom)),
                copycount.value))
    log.info(
        'It took %s to copy for all zoomlevels (total %s)' %
        (str(
            datetime.timedelta(
                seconds=time.time() -
                t0)),
     copycount.value))


class S3Keys:

    def __init__(self, prefix):
        self.bucket = getBucket()
        self.counter = 0
        self.prefix = basePath
        if prefix is not None:
            self.prefix += prefix
        else:
            raise Exception('One must define a prefix')
        self.keysList = self.bucket.list(prefix=self.prefix)

    def delete(self):
        keysToDelete = []
        print 'Are you sure you want to delete all tiles starting with %s? (y/n)' % self.prefix
        answer = raw_input('> ')
        if answer.lower() != 'y':
            sys.exit(1)
        print 'Deleting keys for prefix %s...' % self.prefix
        for key in self.keysList:
            keysToDelete.append(key)
            if len(keysToDelete) % 1000 == 0:
                self._deleteKeysResults(self.bucket.delete_keys(keysToDelete))
                keysToDelete = []
        if len(keysToDelete) > 0:
            self._deleteKeysResults(self.bucket.delete_keys(keysToDelete))
        print '%s keys have been deleted' % self.counter

    def listKeys(self):
        print 'Listing keys for prefix %s...' % self.prefix
        for key in self.keysList:
            print "{name}\t{size}\t{modified}".format(
                name=key.name,
                size=key.size,
                modified=key.last_modified,
            )
            # So that one can interrput it from keyboard
            time.sleep(.2)

    def count(self):
        print 'Counting keys for prefix %s...' % self.prefix
        nbKeys = len(list(self.keysList))
        print '%s keys have been found for prefix %s' % (nbKeys, self.prefix)

    def _deleteKeysResults(self, results):
        nbDeleted = len(results.deleted)
        print '%s could not be deleted.' % len(results.errors)
        print '%s have been deleted.' % nbDeleted
        self.counter += len(results.deleted)


def _getSQSConn():
    try:
        conn = boto.sqs.connect_to_region('eu-west-1', profile_name=profileName)
    except Exception as e:
        raise Exception('SQS: Error during connection %s' % e)
    return conn


connSQS = _getSQSConn()


def getSQS():
    return connSQS


def writeSQSMessage(q, message):
    m = boto.sqs.message.Message()
    m.set_body(message)
    q.write(m)
