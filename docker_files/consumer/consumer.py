"""
    Hello world `receive.py` example implementation using aioamqp.
    See the documentation for more informations.
"""

import asyncio
import aioamqp
import json
import psycopg2


def database(key):
    con = psycopg2.connect(dbname='rabbit', user='postgres', host='172.17.0.5', port=5432, password='qwer1234')
    cur = con.cursor()
    cur.execute("""SELECT v FROM data WHERE k='{}';""".format(key))
    res = cur.fetchone()
    if res:
        response = {'k': key, 'v': res}
    else:
        response = {'k': key, 'v': 'No such key'}
    cur.close()
    con.commit()
    con.close()
    return response


async def on_request(channel, body, envelope, properties):
    data = json.loads(body.decode("utf-8"))

    print(" [.] GETTING value for key: {}".format(data['k']))
    r = database(data['k'])

    await channel.queue_declare(queue_name=proper)

    await channel.basic_publish(
        payload=json.dumps(r),
        exchange_name='',
        routing_key=properties.reply_to,
        properties={
            'correlation_id': properties.correlation_id,
        },
    )
    print(" [x] Done")
    await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)


@asyncio.coroutine
def callback(channel, body, envelope, properties):

    data = json.loads(body.decode("utf-8"))
    if data['action'] == 'set':
        key = data['k']
        value = data['v']
        con = psycopg2.connect(dbname='rabbit', user='postgres', host='172.17.0.5', port=5432, password='qwer1234')
        cur = con.cursor()
        cur.execute("""SELECT v FROM data WHERE k='{}';""".format(key))
        res = cur.fetchone()
        if res:
            cur.execute("""UPDATE data SET v='{}' WHERE k='{}';""".format(value, key))
            print(" [.] Updated {} | {}".format(key, value))
        else:
            cur.execute("""INSERT INTO data (k, v) VALUES ('{}', '{}');""".format(key, value))
            print(" [.] Added {} | {}".format(key, value))
        cur.close()
        con.commit()
        con.close()

    print(" [x] Done")


async def main():

    transport, protocol = await aioamqp.connect(host='172.17.0.2', port=5672)
    channel = await protocol.channel()

    await channel.queue_declare(queue_name='send')
    await channel.queue_declare(queue_name='rpc')

    await channel.basic_qos(prefetch_count=1, prefetch_size=0, connection_global=False)

    await channel.basic_consume(callback, queue_name='send', no_ack=True)
    await channel.basic_consume(on_request, queue_name='rpc')
    print("======== Running ========\n(Press CTRL+C to quit)")


# creating database table if it does not exist


def create_table():
    con = psycopg2.connect(dbname='rabbit', user='postgres', host='172.17.0.5', port=5432, password='qwer1234')
    cur = con.cursor()
    cur.execute("""CREATE TABLE data (
                id SERIAL PRIMARY KEY,
                k varchar(255) NOT NULL,
                v varchar(255)
                );""")
    cur.close()
    con.commit()
    con.close()

try:
    create_table()
except:
    pass

event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(main())
event_loop.run_forever()


