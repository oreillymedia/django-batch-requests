'''
@author: Rahul Tanwani

@summary: A module to perform batch request processing.
'''
from __future__ import absolute_import, unicode_literals

import json
import logging
from datetime import datetime

import six
from concurrent.futures import TimeoutError
from django.conf import settings
from django.http.response import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.urls import resolve
from django.urls.exceptions import Resolver404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from batch_requests.exceptions import BadBatchRequest
from batch_requests.settings import br_settings as _settings
from batch_requests.utils import get_wsgi_request_object


log = logging.getLogger(__name__)


DURATION_HEADER_NAME = _settings.DURATION_HEADER_NAME
UNKNOWN_STATUSES = {
    207: "Multiple Statuses",
    429: "Too Many Requests",
}
VALID_HTTP_METHODS = {
    "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS",
    "CONNECT", "TRACE"
}


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, six.binary_type):
            return obj.decode("utf-8")

        return super(BytesEncoder, self).default(obj)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (set, frozenset)):
            return list(obj)

        return super(SetEncoder, self).default(obj)


def timeout_result_handler(future, timeout=None):
    """Allow timing out concurrent requests"""

    try:
        result = future.result(timeout=timeout)
    except TimeoutError:
        result = {
            "status_code": 408,
            "reason_phrase": "Request Timeout",
            "body": "",
            "headers": {},
        }

    return result


def handle_sub_response_body(response):
    body = getattr(response, "rendered_content", None) or response.content
    if body and _settings.DESERIALIZE_RESPONSES:
        try:
            return json.loads(body)
        except ValueError:
            pass  # fall through and just return body

    return body


def handle_sub_reason_phrase(response, unknown=UNKNOWN_STATUSES):
    phrase = unknown.get(response.status_code, None)
    if phrase:
        return phrase

    return response.reason_phrase


def construct_duration_header(duration):
    return duration.seconds + (duration.microseconds / 1000000.0)


def add_duration_header(resp, start, end):
    resp["headers"][DURATION_HEADER_NAME] = construct_duration_header(end - start)


def get_response(wsgi_request):
    '''
        Given a WSGI request, makes a call to a corresponding view
        function and returns the response.
    '''
    resp = None
    service_start_time = datetime.now()
    # Get the view / handler for this request
    try:
        view, args, kwargs = resolve(wsgi_request.path_info)
    except Resolver404:
        resp = HttpResponseNotFound()

    if resp is None:
        kwargs.update({"request": wsgi_request})

        # Let the view do his task.
        try:
            resp = view(*args, **kwargs)
        except Exception as exc:
            resp = HttpResponseServerError(content=str(exc))

    # Convert HTTP response into simple dict type.
    d_resp = {
        "status_code": resp.status_code,
        "reason_phrase": handle_sub_reason_phrase(resp),
        "headers": {k: v for k, v in six.itervalues(resp._headers)},
        "body": handle_sub_response_body(resp),
    }

    # Check if we need to send across the duration header.
    if _settings.ADD_DURATION_HEADER:
        add_duration_header(d_resp, service_start_time, datetime.now())

    return d_resp


def get_wsgi_requests(request):
    '''
        For the given batch request, extract the individual requests and create
        WSGIRequest object for each.
    '''
    body = request.body.decode('utf-8')
    requests = json.loads(body)

    if not isinstance(requests, (list, tuple)):
        raise BadBatchRequest("The body of batch request should always be list!")

    if len(requests) > _settings.MAX_LIMIT:
        raise BadBatchRequest("You can batch maximum of %d requests." % (_settings.MAX_LIMIT))

    # We could mutate the current request with the respective parameters, but
    # mutation is ghost in the dark, so lets avoid. Construct the new WSGI
    # request object for each request.
    def construct_wsgi_from_data(data, valid_http_methods=VALID_HTTP_METHODS):
        '''
            Given the data in the format of url, method, body and headers, construct a new
            WSGIRequest object.
        '''
        url = data.get("url", None)
        method = data.get("method", None)

        if url is None or method is None:
            raise BadBatchRequest("Request definition should have url, method defined.")

        method = method.upper()
        if method not in valid_http_methods:
            raise BadBatchRequest("Invalid request method.")

        # support singly/doubly encoded JSON
        body = data.get("body", "")
        if isinstance(body, dict):
            body = json.dumps(body, cls=BytesEncoder)
        headers = data.get("headers", {})
        return get_wsgi_request_object(request, method, url, headers, body)

    return (construct_wsgi_from_data(data) for data in requests)


def execute_requests(wsgi_requests):
    '''
        Execute the requests either sequentially or in parallel based on parallel
        execution setting.
    '''
    return _settings.executor.execute(
        wsgi_requests, get_response, result_handler=timeout_result_handler
    )


@csrf_exempt
@require_http_methods(["POST"])
def handle_batch_requests(request, *args, **kwargs):
    '''
        A view function to handle the overall processing of batch requests.
    '''
    try:
        # Get the Individual WSGI requests.
        wsgi_requests = get_wsgi_requests(request)
    except BadBatchRequest as brx:
        return HttpResponseBadRequest(content=six.text_type(brx))

    batch_start_time = datetime.now()

    # Fire these WSGI requests, and collect the response for the same.
    try:
        response = execute_requests(wsgi_requests)
    except BadBatchRequest as brx:
        return HttpResponseBadRequest(content=six.text_type(brx))

    batch_end_time = datetime.now()
    BATCH_RESPONSE_STATUS = _settings.BATCH_RESPONSE_STATUS

    # Evrything's done, return the response.
    resp_kwargs = {
        "content": json.dumps(response, cls=BytesEncoder),
        "content_type": "application/json",
        "status": BATCH_RESPONSE_STATUS,
    }

    # handle STDLIB unknown reason phrases
    batch_reason = UNKNOWN_STATUSES.get(BATCH_RESPONSE_STATUS, None)
    if batch_reason:
        resp_kwargs["reason"] = batch_reason

    resp = HttpResponse(**resp_kwargs)

    if _settings.DISALLOW_CACHING:
        resp["Cache-Control"] = "Private"

    if _settings.ADD_DURATION_HEADER:
        resp[DURATION_HEADER_NAME] = construct_duration_header(batch_end_time - batch_start_time)

    if settings.DEBUG:
        resp[_settings.DEBUG_HEADER_NAME] = json.dumps(_settings.as_dict(), cls=SetEncoder)

    return resp
