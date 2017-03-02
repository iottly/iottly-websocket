"""

Copyright 2015 Stefano Terna

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""
import json
import logging
import os
import tornado
import tornado.web
import tornado.ioloop
from tornado import gen, autoreload

from sockjs.tornado import SockJSRouter, SockJSConnection

import pika
from threading import Thread



from iottly_websocket.settings import settings
from iottly_websocket.util import module_to_dict

logging.getLogger().setLevel(logging.DEBUG)

connected_clients=set()


class MessagesConnection(SockJSConnection):
    def on_open(self, info):
        connected_clients.add(self)

    def on_close(self):
        connected_clients.remove(self)



def shutdown():
    logging.info('shutting down')

if __name__ == "__main__":
    WebSocketRouter = SockJSRouter(MessagesConnection, '/messageChannel')
    app_settings = module_to_dict(settings)
    autoreload.add_reload_hook(shutdown)

    application = tornado.web.Application(
        WebSocketRouter.urls,         
        **app_settings
    )

    application.listen(8520)
    logging.info(" [*] Listening on 0.0.0.0:8520")

    tornado.ioloop.IOLoop.instance().start()

