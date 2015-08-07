# -*- coding: utf-8 -*-

import time
import multiprocessing
import signal
import ConfigParser

from forge.lib.logs import getLogger
from forge.lib.helpers import timestamp

NUMBER_POOL_PROCESSES = multiprocessing.cpu_count()

dbConfig = ConfigParser.RawConfigParser()
dbConfig.read('database.cfg')
logger = getLogger(dbConfig, __name__, suffix=timestamp())


# Assure that sub processes don't get keyborad interrupts
def initProcess():
    logger.info('Starting process id: %s' % multiprocessing.current_process().pid)
    signal.signal(signal.SIGINT, signal.SIG_IGN)


class PoolManager:

    def __init__(self):
        self._pool = multiprocessing.Pool(NUMBER_POOL_PROCESSES, initProcess)

    def _abort(self):
        self._pool.terminate()
        self._pool.join()

    def numOfProcesses(self):
        return NUMBER_POOL_PROCESSES

    # Blocking call
    def process(self, iterable, func, chunks):
        self._pool.imap_unordered(func, iterable, chunks)
        self._pool.close()
        try:
            while len([p for p in self._pool._pool if p.is_alive()]) > 0:
                time.sleep(3)
        except KeyboardInterrupt:
            logger.info('Keyboard interupt recieved, terminating workers...')
            self._abort()
        except Exception as e:
            logger.error('Error while processing: %s' % e)
            self._abort()
            raise Exception(e)
        self._pool.join()
