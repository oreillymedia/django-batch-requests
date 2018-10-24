'''
Created on Feb 20, 2016

@author: Rahul Tanwani
'''
from __future__ import absolute_import, unicode_literals

from abc import ABCMeta

from concurrent.futures._base import Executor as BaseExecutor, Future
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor


def default_result_handler(future, *args, **kwargs):
    return future.result()


class SequentialPoolExecutor(BaseExecutor):
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def submit(self, fn, *args, **kwargs):
        f = Future()
        try:
            result = fn(*args, **kwargs)
        except BaseException as exc:
            f.set_exception(exc)
            # Break a reference cycle with the exception 'exc', copied from stdlib
            self = None  # noqa: W0612
        else:
            f.set_result(result)
        return f


class Executor(object):
    '''Based executor class to encapsulate the job execution.'''
    __metaclass__ = ABCMeta

    def __init__(self, num_workers, timeout=None):
        '''Create a pool for (maybe) concurrent execution with specified number of workers.'''
        self.num_workers = num_workers
        self.timeout = timeout

    def get_executor_pool(self, num_workers=None):
        return self.executor_cls(num_workers or self.num_workers)

    def execute(self, requests, resp_generator,
                result_handler=default_result_handler,
                *args, **kwargs):
        '''Calls the resp_generator for all the requests in parallel in an asynchronous way'''
        with self.get_executor_pool() as pool:
            futures = [
                pool.submit(resp_generator, r, *args, **kwargs)
                for r in requests
            ]

        timeout = self.timeout
        return [result_handler(f, timeout) for f in futures]


class SequentialExecutor(Executor):
    '''An implementation of executor using no parallelism.'''
    executor_cls = SequentialPoolExecutor


class ThreadBasedExecutor(Executor):
    '''An implementation of executor using threads for parallelism.'''
    executor_cls = ThreadPoolExecutor


class ProcessBasedExecutor(Executor):
    '''An implementation of executor using process(es) for parallelism.'''
    executor_cls = ProcessPoolExecutor
