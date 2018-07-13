'''
@author: Rahul Tanwani

@summary: Contains base test case for reusable test methods.
'''
from __future__ import unicode_literals

import json

import django
from django.test import TestCase

from batch_requests.settings import br_settings as settings
from . import ensure_text_content


class TestBase(TestCase):

    '''
        Base class for all reusable test methods.
    '''

    def assert_reponse_compatible(self, ind_resp, batch_resp):
        '''
            Assert if the response of independent request is compatible with
            batch response.
        '''
        # Remove duration header to compare.
        if settings.ADD_DURATION_HEADER:
            del batch_resp['headers'][settings.DURATION_HEADER_NAME]

        # if Django >= 1.11, Content-Length header added
        # TODO: fix this so we don't have to work around it
        if django.VERSION >= (1, 11) and 'Content-Length' in ind_resp['headers']:
            del ind_resp['headers']['Content-Length']

        self.assertDictEqual(ind_resp, batch_resp, "Compatibility is broken!")

    def headers_dict(self, headers):
        '''
            Converts the headers from the response in to a dict.
        '''
        return dict(headers.values())

    def prepare_response(self, status_code, body, headers):
        '''
            Returns a dict of all the parameters.
        '''
        return {
            "status_code": status_code,
            "body": body,
            "headers": self.headers_dict(headers)
        }

    def _batch_request(self, method, path, data, headers={}):
        '''
            Prepares a batch request.
        '''
        return {
            "url": path,
            "method": method,
            "headers": headers,
            "body": data
        }

    def make_a_batch_request(self, method, url, body, headers={}):
        '''
            Makes a batch request using django client.
        '''
        return ensure_text_content(self.client.post(
            "/api/v1/batch/",
            json.dumps([self._batch_request(method, url, body, headers)]),
            content_type="application/json"
        ))

    def make_multiple_batch_request(self, requests):
        '''
            Makes multiple batch request using django client.
        '''
        batch_requests = [
            self._batch_request(method, path, data, headers)
            for method, path, data, headers in requests
        ]
        return ensure_text_content(self.client.post(
            "/api/v1/batch/",
            json.dumps(batch_requests),
            content_type="application/json"
        ))
