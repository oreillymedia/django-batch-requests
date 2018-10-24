'''
@author: Rahul Tanwani

@summary: Test cases to check  the behavior when the batch request is
          not constructed properly.
'''
import json

import mock
import pytest
from django.test import TestCase

from tests import ensure_text_content


class TestBadBatchRequest(TestCase):

    '''
        Check the behavior of bad batch request.
    '''

    def _batch_request(self, method, path, data, headers={}):
        '''
            Prepares a batch request.
        '''
        return {"url": path, "method": method, "headers": headers, "body": data}

    def test_invalid_http_method(self):
        '''
            Make a batch request with invalid HTTP method.
        '''
        resp = ensure_text_content(
            self.client.post(
                "/api/v1/batch/",
                json.dumps([self._batch_request("select", "/views", "", {})]),
                content_type="application/json"
            )
        )

        self.assertEqual(resp.status_code, 400, "Method validation is broken!")
        self.assertEqual(resp.text.lower(), "invalid request method.", "Method validation is broken!")

    def test_missing_http_method(self):
        '''
            Make a batch request without HTTP method.
        '''
        resp = ensure_text_content(
            self.client.post(
                "/api/v1/batch/",
                json.dumps([{"body": "/views"}]),
                content_type="application/json"
            )
        )

        self.assertEqual(resp.status_code, 400, "Method & URL validation is broken!")
        self.assertEqual(resp.text.lower(), "request definition should have url, method defined.", "Method validation is broken!")

    def test_missing_url(self):
        '''
            Make a batch request without the URL.
        '''
        resp = ensure_text_content(
            self.client.post(
                "/api/v1/batch/",
                json.dumps([{"method": "get"}]),
                content_type="application/json"
            )
        )

        self.assertEqual(resp.status_code, 400, "Method & URL validation is broken!")
        self.assertEqual(resp.text.lower(), "request definition should have url, method defined.",
                         "Method validation is broken!")

    def test_invalid_batch_request(self):
        '''
            Make a batch request without wrapping in the list.
        '''
        resp = ensure_text_content(
            self.client.post(
                "/api/v1/batch/",
                json.dumps({"method": "get", "url": "/views/"}),
                content_type="application/json"
            )
        )

        self.assertEqual(resp.status_code, 400, "Batch requests should always be in list.")
        self.assertEqual(resp.text.lower(), "the body of batch request should always be list!",
                         "List validation is broken!")

    def test_view_that_raises_exception(self):
        '''
            Make a batch request to a view that raises exception.
        '''
        with self.settings(DEBUG=True):
            resp = ensure_text_content(
                self.client.post(
                    "/api/v1/batch/",
                    json.dumps([
                        {"method": "get", "url": "/exception/"},
                        {"method": "get", "url": "/rate-limited/"},
                        {"method": "get", "url": "/views/"},
                    ]),
                    content_type="application/json"
                )
            )

        assert resp.status_code == 200
        responses = json.loads(resp.text)

        expected = {
            0: (500, 'exception'),
            1: (429, 'rate limited'),
            2: (200, 'success!'),
        }

        for index, expects in expected.items():
            resp = responses[index]
            exp_status, exp_explanation = expects
            assert resp['status_code'] == exp_status
            assert resp['body'].lower() == exp_explanation

    @pytest.mark.regression
    def test_exception_view_with_deserialization(self):
        """Make batch request to exception endpoint AND try to deserialize the response"""
        with mock.patch('batch_requests.views._settings.DESERIALIZE_RESPONSES') as mock_des:
            mock_des.return_value = True
            resp = ensure_text_content(
                self.client.post(
                    "/api/v1/batch/",
                    json.dumps([{"method": "get", "url": "/exception/"}]),
                    content_type="application/json"
                )
            )

        assert resp.status_code == 200
        responses = json.loads(resp.text)
        assert responses[0]['status_code'] == 500
