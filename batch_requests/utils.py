'''
@author: Rahul Tanwani

@summary: Holds all the utilities functions required to support batch_requests.
'''
from __future__ import absolute_import, unicode_literals

import six
from django.test.client import RequestFactory, FakePayload

from batch_requests.settings import br_settings as _settings


# Standard WSGI supported headers
WSGI_HEADERS = {
    "CONTENT_LENGTH", "CONTENT_TYPE", "QUERY_STRING", "REMOTE_ADDR",
    "REMOTE_HOST", "REMOTE_USER", "REQUEST_METHOD", "SERVER_NAME",
    "SERVER_PORT",
}


class BatchRequestFactory(RequestFactory):

    '''
        Extend the RequestFactory and update the environment variables for WSGI.
    '''

    def _base_environ(self, **request):
        '''
            Override the default values for the wsgi environment variables.
        '''
        # This is a minimal valid WSGI environ dictionary, plus:
        # - HTTP_COOKIE: for cookie support,
        # - REMOTE_ADDR: often useful, see #8551.
        # See http://www.python.org/dev/peps/pep-3333/#environ-variables

        environ = {
            'HTTP_COOKIE': self.cookies.output(header='', sep='; '),
            'PATH_INFO': str('/'),
            'REMOTE_ADDR': str('127.0.0.1'),
            'REQUEST_METHOD': str('GET'),
            'SCRIPT_NAME': str(''),
            'SERVER_NAME': str('localhost'),
            'SERVER_PORT': str('8000'),
            'SERVER_PROTOCOL': str('HTTP/1.1'),
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': str('http'),
            'wsgi.input': FakePayload(b''),
            'wsgi.errors': self.errors,
            'wsgi.multiprocess': True,
            'wsgi.multithread': True,
            'wsgi.run_once': False,
        }
        environ.update(self.defaults)
        environ.update(request)
        return environ


def get_wsgi_request_object(
    curr_request, method, url, headers, body,
    REQUEST_FACTORY=BatchRequestFactory()  # purposefully using a shared instance
):
    '''
        Based on the given request parameters, constructs and returns the WSGI request object.
    '''
    def transform_header(header, _wsgi_headers=WSGI_HEADERS):
        """Transform headers, if necessary

        For every header, replace - to _, prepend http_ if necessary and
        convert to upper case.
        """
        header = header.replace("-", "_").upper()
        if header not in _wsgi_headers:
            header = "HTTP_{header}".format(header=header)
        return header

    t_headers = {"CONTENT_TYPE": _settings.DEFAULT_CONTENT_TYPE}
    t_headers.update({
        transform_header(h): v for h, v in six.iteritems(headers)
    })

    # Override existing batch requests headers with the new headers passed for this request.
    x_headers = {
        h: v for h, v in six.iteritems(curr_request.META)
        if h in _settings.HEADERS_TO_INCLUDE
    }
    x_headers.update(t_headers)

    return getattr(REQUEST_FACTORY, method.lower())(
        url,
        data=body,
        secure=_settings.USE_HTTPS,
        content_type=x_headers.get("CONTENT_TYPE", _settings.DEFAULT_CONTENT_TYPE),
        **x_headers
    )
