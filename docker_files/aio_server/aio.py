import asyncio
from aiohttp import hdrs, web
import aiohttp_cors
import aioamqp
import json
import uuid


class Get(object):
    def __init__(self):
        self.transport = None
        self.protocol = None
        self.channel = None
        self.callback_queue = None
        self.waiter = asyncio.Event()
        self.response = None
        self.corr_id = None

    async def connect(self):
        self.transport, self.protocol = await aioamqp.connect(host='172.17.0.2', port=5672)
        self.channel = await self.protocol.channel()

        await self.channel.queue_declare(queue_name='callback_queue')
        self.callback_queue = 'callback_queue'

        await self.channel.basic_consume(self.on_response, no_ack=True, queue_name=self.callback_queue)

    async def on_response(self, channel, body, envelope, properties):
        if self.corr_id == properties['correlation_id']:
            self.response = body

        self.waiter.set()

    async def call(self, n):
        if not self.protocol:
            await self.connect()
        await self.channel.queue_declare(queue_name='rpc', no_ack=True)
        self.response = b'{"k": "error", "v": "no response"}'
        self.corr_id = str(uuid.uuid4())
        await self.channel.basic_publish(
            payload=json.dumps({'action': 'get', 'k': n}),
            exchange_name='',
            routing_key='rpc',
            properties={
                'reply_to': self.callback_queue,
                'correlation_id': self.corr_id,
            },
        )
        await self.waiter.wait()
        # await self.protocol.close()
        # self.transport.close()

        return json.loads(self.response.decode("utf-8"))


# PONIŻEJ KOD DZIAŁAJĄCY (W PEWNYM SENSIE)

# async def on_response(channel, body, envelope, properties):
#     if corr_id == properties['correlation_id']:
#         response = body
#     waiter.set()
#
#
#     # return response
#
#
async def call(n):
    transport, protocol = await aioamqp.connect(host='172.17.0.2', port=5672)
    channel = await protocol.channel()

    await channel.queue_declare(queue_name='rpc')

    # ch = await channel.queue_declare()
    # callback_queue = ch['queue_name']

    # global corr_id
    # corr_id = str(uuid.uuid4())

    await channel.basic_publish(
        payload=json.dumps({'action': 'get', 'k': n}),
        exchange_name='',
        routing_key='rpc',
        properties={
            'reply_to': callback_queue,
            'correlation_id': corr_id,
        },
    )

    response = None

    await channel.basic_consume(on_response, no_ack=True, queue_name=callback_queue)

    await waiter.wait()

    try:
        channel.queue_delete(queue_name=callback_queue)
    except aioamqp.exceptions.ChannelClosed:
        print('Does not work')

    await protocol.close()
    r = json.loads(response.decode("utf-8"))
    return r


async def rpc_client(key):
    # g = Get()
    print(" [.] Requesting value for key: {}".format(key))
    response = await call(key)
    print(" [x] Got %r" % response['v'])
    return response


async def send(key, value=0):
    transport, protocol = await aioamqp.connect(host='172.17.0.2', port=5672)
    channel = await protocol.channel()

    await channel.queue_declare(queue_name='send')

    await channel.basic_publish(
        payload=json.dumps({'action': 'set', 'k': key, 'v': value}),
        exchange_name='',
        routing_key='send',
    )

    try:
        channel.queue_delete(queue_name='send', if_empty=True)
    except aioamqp.exceptions.ChannelClosed:
        print('Not working')
    await protocol.close()
    transport.close()


class KeyValueService(web.View):

    async def get(self):
        key = self.request.match_info.get('key')
        value = None
        try:
            value = self.request.match_info.get('value')
        except:
            pass
        if value is not None:
            await send(key, value)

            text = '[x] SENT --------- Key: ' + key + '  Value: ' + value
        else:
            # try:
                await asyncio.sleep(1)
                a = await rpc_client(key)
                if a['v'] == 'No such key':
                    text = '[o] NO SUCH KEY -------- Key: '+key
                else:
                    text = '[x] GOT ------ Key: ' + key + ' Value: ' + a['v']
            # except:
            #     text = 'No such key in database'
        return web.Response(text=text)


app = web.Application()
cors = aiohttp_cors.setup(app)

resource = cors.add(app.router.add_resource('/{key}'))
route = cors.add(resource.add_route("GET", KeyValueService), {
    "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            max_age=3600,
    )
})
resource = cors.add(app.router.add_resource('/{key}/{value}'))
route1 = cors.add(resource.add_route("GET", KeyValueService), {
    "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            max_age=3600,
    )
})

web.run_app(app, host='0.0.0.0', port=80)
