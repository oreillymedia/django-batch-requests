'''
@author: Rahul Tanwani

@summary: Contains base test case for concurrency related tests.
'''
from __future__ import absolute_import, unicode_literals

import json

from batch_requests.settings import br_settings as _settings
from tests.test_base import TestBase


class TestBaseConcurrency(TestBase):
    '''
        Base class for all reusable test methods related to concurrency.
    '''
    # FIXME: Find the better way to manage / update settings.
    def setUp(self):
        '''
            Change the concurrency settings.
        '''
        self.number_workers = 10
        self.orig_executor = _settings.executor

    def tearDown(self):
        # Restore the original batch requests settings.
        _settings.executor = self.orig_executor

    def compare_seq_and_concurrent_req(self):
        '''
            Make a request with sequential and concurrency based executor and compare
            the response.
        '''
        data = json.dumps({"text": "Batch"})

        # Make a batch call for GET, POST and PUT request.
        get_req = ("get", "/views/", '', {})
        post_req = ("post", "/views/", data, {"content_type": "text/plain"})
        put_req = ("put", "/views/", data, {"content_type": "text/plain"})

        # Get the response for a batch request.
        batch_requests = self.make_multiple_batch_request([get_req, post_req, put_req])

        # FIXME: Find the better way to manage / update settings.
        # Update the settings.
        _settings.executor = self.get_executor()
        threaded_batch_requests = self.make_multiple_batch_request([get_req, post_req, put_req])

        seq_responses = json.loads(batch_requests.content.decode("utf-8"))
        conc_responses = json.loads(threaded_batch_requests.content.decode("utf-8"))

        for idx, seq_resp in enumerate(seq_responses):
            conc_resp = conc_responses[idx]

            # durations are now more finegrained, compare them separately
            conc_duration = conc_resp["headers"].pop(_settings.DURATION_HEADER_NAME)
            seq_duration = seq_resp["headers"].pop(_settings.DURATION_HEADER_NAME)

            # using 10ms as a current error bounds on durations
            assert abs(float(conc_duration) - float(seq_duration)) <= 0.010
            assert seq_resp == conc_resp

    def compare_seq_concurrent_duration(self):
        '''
            Makes the batch requests run sequentially and in parallel and asserts
            parallelism to reduce the total duration time.
        '''
        # Make a batch call for GET, POST and PUT request.
        sleep_2_seconds = ("get", "/sleep/?seconds=1", '', {})
        sleep_1_second = ("get", "/sleep/?seconds=1", '', {})

        # Get the response for a batch request.
        batch_requests = self.make_multiple_batch_request([sleep_2_seconds, sleep_1_second, sleep_2_seconds])
        seq_duration = float(
            batch_requests._headers.get(_settings.DURATION_HEADER_NAME)[1]
        )

        # Update the executor settings.
        _settings.executor = self.get_executor()
        concurrent_batch_requests = self.make_multiple_batch_request([sleep_2_seconds, sleep_1_second, sleep_2_seconds])
        concurrency_duration = float(
            concurrent_batch_requests._headers.get(_settings.DURATION_HEADER_NAME)[1]
        )

        self.assertLess(concurrency_duration, seq_duration, "Concurrent requests are slower than running them in sequence.")
