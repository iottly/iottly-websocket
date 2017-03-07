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

# TODO: refactor with suggested approach:
# http://pika.readthedocs.io/en/0.10.0/examples/tornado_consumer.html

# TODO: fix reconnection

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

logging.getLogger().setLevel(logging.INFO)

connected_clients={}

rabbitconnection = pika.BlockingConnection(pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST))
logging.info('rabbitconnection: {}'.format(settings.RABBITMQ_HOST))

rabbitchannel = rabbitconnection.channel()

def threaded_rmq():
    queuename = settings.QUEUE_NAME
    rabbitchannel.queue_declare(queue=queuename)
    logging.info('consumer ready, on websocketqueue')
    rabbitchannel.basic_consume(consumer_callback, queue=queuename, no_ack=True) 
    rabbitchannel.start_consuming()

def disconnect_to_rabbitmq():
    rabbitchannel.stop_consuming()
    rabbitchannel.close()
    rabbitconnection.close()
    logging.info('Disconnected from Rabbitmq')

def consumer_callback(ch, method, properties, body):
    msg = json.loads(body)
    projectid = msg.get('projectid',None)
    if projectid:
        del msg['projectid']
        for client in connected_clients.get(projectid, []):
            logging.info('client: {} - msg: {}'.format(client, msg))
            client.send(json.dumps(msg))


class MessagesConnection(SockJSConnection):
        
    def on_open(self, info):
        # if client has not yet been connected to a project
        # identify it with some dummy key and possibly discard on close
        self.projectid = 'temporary-dummy-key'

    def on_close(self):
        logging.info('remove client')
        projectid = self.projectid
        project_clients = connected_clients.get(projectid, [])
        if self in project_clients:
            project_clients.remove(self)
        connected_clients[projectid] = project_clients
        
    def on_message(self, msg):
        projectid = json.loads(msg).get('projectid')
        self.projectid = projectid
        project_clients = connected_clients.get(projectid, [])
        project_clients.append(self)
        connected_clients[projectid] = project_clients
        



def shutdown():
    logging.info('shutting down')
    disconnect_to_rabbitmq()
    tornado.ioloop.IOLoop.instance().stop()

if __name__ == "__main__":

    logging.info('Starting thread RabbitMQ')
    threadRMQ = Thread(target=threaded_rmq)
    threadRMQ.start()

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

    shutdown()