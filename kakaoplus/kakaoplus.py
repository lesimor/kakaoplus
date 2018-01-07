import sys
import json
import re

from .payload import Payload
from .template import *
from .utils import to_json, PY3, _byteify, LOGGER

class Req(object):
    def __init__(self, data):
        if not PY3:
            self.data  = json.loads(data, object_hook=_byteify)
        else:
            self.data  = json.loads(data)

    @property
    def user_key(self):
        return self.data.get('user_key')

    @property
    def message_type(self):
        return self.data.get('type')

    @property
    def content(self):
        return self.data.get('content')

    @property
    def recieved_photo(self):
        return self.message_type == 'photo'

    @property
    def recieved_text(self):
        return self.message_type == 'text'


class KaKaoAgent(object):
    _message_callbacks = {}
    _message_callbacks_key_regex = {}
    _photo_handler = None
    _default_callback = None

    def handle_webhook(self, request):
        req = Req(request)

        if req.recieved_photo:
            matched_callback = self._photo_handler
        elif req.recieved_text:
            matched_callback = self.get_message_callback(req)
        else:
            LOGGER.warn('Unknown type %s' % req.message_type)
            return "ok"

        if matched_callback is not None:
            res = matched_callback(req)
        else:
            print("There is no matching handler")
            return "ok"

        if not isinstance(res, Payload):
            raise ValueError('Return type must be Payload')

        return res.to_json()

    '''
    decorators
    '''
    def photo_handler(self, func):
        self._photo_handler = func

    '''
    setting regular expressions
    '''
    def handle_message(self, payloads=None):
        if callable(payloads):
            self._default_callback = payloads
            return
        def wrapper(func):
            for payload in payloads:
                self._message_callbacks[payload] = func
            return func

        return wrapper

    def get_message_callback(self, req):
        callback = None
        for key in self._message_callbacks.keys():
            if key not in self._message_callbacks_key_regex:
                self._message_callbacks_key_regex[key] = re.compile(key + '$')
        for key in self._message_callbacks.keys():
            if self._message_callbacks_key_regex[key].match(req.content):
                callback = self._message_callbacks[key]
                LOGGER.info("matched message handler %s"%key)
                break
        if callback is None:
            LOGGER.info("default message handler")
            callback = self._default_callback

        return callback

    def handle_keyboard(self, func):
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            return to_json(res)

        return wrapper