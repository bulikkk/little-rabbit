"""
    Hello world `receive.py` example implementation using aioamqp.
    See the documentation for more informations.
"""

import asyncio
import aioamqp
from aiohttp import web
import json
import _mysql


def database(key):
    con = _mysql.connect("localhost", "root", "coderslab", "rabbit")
    con.query("""SELECT v FROM data WHERE k='{}';""".format(key))
    r = con.store_result()
    res = r.fetch_row(how=1)
    if res:
        response = {'k': key, 'v': res[0]['v'].decode("utf-8")}
    else:
        response = {'k': key, 'v': 'No such key'}
    con.close()
    return response


@asyncio.coroutine
def on_request(channel, body, envelope, properties):
    data = json.loads(body.decode("utf-8"))

    print(" [.] GETTING value for key: {}".format(data['k']))
    response = database(data['k'])

    yield from channel.basic_publish(
        payload=json.dumps(response),
        exchange_name='',
        routing_key=properties.reply_to,
        properties={
            'correlation_id': properties.correlation_id,
        },
    )
    print(" [x] Done")
    yield from channel.basic_client_ack(delivery_tag=envelope.delivery_tag)


@asyncio.coroutine
def callback(channel, body, envelope, properties):

    data = json.loads(body.decode("utf-8"))
    if data['action'] == 'set':
        key = data['k']
        value = data['v']
        con = _mysql.connect("localhost", "root", "coderslab", "rabbit")
        con.query("""SELECT v FROM data WHERE k='{}';""".format(key))
        r = con.store_result()
        res = r.fetch_row(how=1)
        if res:
            con.query("""UPDATE data SET v='{}' WHERE k='{}';""".format(value, key))
            print(" [.] Updated {} | {}".format(key, value))
        else:
            con.query("""INSERT INTO data (k, v) VALUES ('{}', '{}');""".format(key, value))
            print(" [.] Added {} | {}".format(key, value))
        con.close()

    print(" [x] Done")


@asyncio.coroutine
def receive():
    transport, protocol = yield from aioamqp.connect()
    channel = yield from protocol.channel()

    yield from channel.queue_declare(queue_name='send')
    yield from channel.queue_declare(queue_name='rpc_queue')

    yield from channel.basic_qos(prefetch_count=1, prefetch_size=0, connection_global=False)

    yield from channel.basic_consume(callback, queue_name='send', no_ack=True)
    yield from channel.basic_consume(on_request, queue_name='rpc_queue')
    print("======== Running ========\n(Press CTRL+C to quit)")


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(receive())

try:
    event_loop.run_forever()
except KeyboardInterrupt:
    pass

app = web.Application()
web.run_app(app, host='127.0.0.1', port=8080)
