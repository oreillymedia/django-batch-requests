from __future__ import unicode_literals

import six


def ensure_text_content(response):
    text = response.content
    if isinstance(response.content, six.binary_type):
        text = response.content.decode("utf-8")

    response.text = text
    return response
