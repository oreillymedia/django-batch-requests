'''
@author: Rahul Tanwani

@summary: Contains the default settings.
'''
import multiprocessing

import six
from django.conf import settings

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module

DEFAULTS = {
    "ADD_DURATION_HEADER": True,
    "BATCH_RESPONSE_STATUS": 200,
    "CONCURRENT_EXECUTOR": "batch_requests.concurrent.executor.ThreadBasedExecutor",
    "DEBUG_HEADER_NAME": "batch_requests.debug",
    "DEFAULT_CONTENT_TYPE": "application/json",
    "DISALLOW_CACHING": False,
    "DURATION_HEADER_NAME": "batch_requests.duration",
    "EXECUTE_PARALLEL": False,
    "HEADERS_TO_INCLUDE": {"HTTP_USER_AGENT", "HTTP_COOKIE"},
    "NUM_WORKERS": multiprocessing.cpu_count() * 4,
    "MAX_LIMIT": 20,
    "REQUEST_TIMEOUT": None,
    "USE_HTTPS": False,

    # JN: added for ORM use
    "DESERIALIZE_RESPONSES": False,
}


USER_DEFINED_SETTINGS = getattr(settings, 'BATCH_REQUESTS', {})


def import_class(class_path):
    '''
        Imports the class for the given class name.
    '''
    module_name, class_name = class_path.rsplit(".", 1)
    module = import_module(module_name)
    claz = getattr(module, class_name)
    return claz


class BatchRequestSettings(object):

    '''
        Allow API settings to be accessed as properties.
    '''

    def __init__(self, user_settings=None, defaults=None):
        self.user_settings = user_settings or {}
        self.defaults = defaults or {}
        self.executor = self._executor()

    def _executor(self):
        '''
            Creating an ExecutorPool is a costly operation. Executor needs to be instantiated only once.
        '''
        executor_path = "batch_requests.concurrent.executor.SequentialExecutor"
        if self.EXECUTE_PARALLEL:
            executor_path = self.CONCURRENT_EXECUTOR

        executor_class = import_class(executor_path)
        return executor_class(self.NUM_WORKERS, self.REQUEST_TIMEOUT)

    def __getattr__(self, attr):
        '''
            Override the attribute access behavior.
        '''

        if attr not in self.defaults:
            raise AttributeError("Invalid API setting: '%s'" % attr)

        val = self.user_settings.get(attr, self.defaults[attr])

        # Cache the result
        setattr(self, attr, val)
        return val

    def as_dict(self):
        return {k: getattr(self, k) for k in six.iterkeys(self.defaults)}


br_settings = BatchRequestSettings(USER_DEFINED_SETTINGS, DEFAULTS)
