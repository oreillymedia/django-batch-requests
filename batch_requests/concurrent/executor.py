'''
Created on Feb 20, 2016

@author: Rahul Tanwani
'''
from __future__ import absolute_import, unicode_literals

from abc import ABCMeta

from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor


def default_result_handler(future, *args, **kwargs):
    return future.result()


class Executor(object):
    '''
        Based executor class to encapsulate the job execution.
    '''
    __metaclass__ = ABCMeta

    def __init__(self, num_workers, timeout=None):
        '''
            Create a thread pool for concurrent execution with specified number of workers.
        '''
        self.num_workers = num_workers
        self.timeout = timeout

    def get_executor_pool(self, num_workers=None):
        return self.executor_cls(num_workers or self.num_workers)

    def execute(self, requests, resp_generator,
                result_handler=default_result_handler,
                *args, **kwargs):
        '''
            Calls the resp_generator for all the requests in parallel in an asynchronous way.
        '''
        pool = self.get_executor_pool()
        timeout = self.timeout
        return [
            result_handler(future, timeout) for future in [
                pool.submit(resp_generator, req, *args, **kwargs)
                for req in requests
            ]
        ]


class SequentialExecutor(Executor):
    '''
        Executor for executing the requests sequentially.
    '''

    def execute(self, requests, resp_generator, *args, **kwargs):
        '''
            Calls the resp_generator for all the requests in sequential order.
        '''
        return [resp_generator(request) for request in requests]


class ThreadBasedExecutor(Executor):
    '''
        An implementation of executor using threads for parallelism.
    '''
    executor_cls = ThreadPoolExecutor


class ProcessBasedExecutor(Executor):
    '''
        An implementation of executor using process(es) for parallelism.
    '''
    executor_cls = ProcessPoolExecutor
