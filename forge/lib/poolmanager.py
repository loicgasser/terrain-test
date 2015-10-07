# -*- coding: utf-8 -*-

import time
import multiprocessing
import signal


class PoolManager:

    def __init__(self, logger, numProcs=multiprocessing.cpu_count(), factor=1):
        self._numProcs = int(numProcs * factor)
        self.logger = logger
        self._pool = multiprocessing.Pool(self._numProcs, self._initProcess)

    def _abort(self):
        self._pool.terminate()
        self._pool.join()

    # Assure that sub processes don't get keyborad interrupts
    def _initProcess(self):
        self.logger.info('Starting process id: %s' % multiprocessing.current_process().pid)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def numOfProcesses(self):
        return self._numProcs

    # Blocking call
    def process(self, iterable, func, chunks):
        self._pool.imap_unordered(func, iterable, chunks)
        self._pool.close()
        try:
            while len([p for p in self._pool._pool if p.is_alive()]) > 0:
                time.sleep(3)
        except KeyboardInterrupt:
            self.logger.info('Keyboard interupt recieved, terminating workers...')
            self._abort()
        except Exception as e:
            self.logger.error('Error while processing: %s' % e, exc_info=True)
            self._abort()
            raise Exception(e)
        self._pool.join()
