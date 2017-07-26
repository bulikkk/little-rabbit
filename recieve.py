#!/usr/bin/env python
import pika
import time
import json
import _mysql


connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='task_queue', durable=True)
print(' [*] Waiting for messages. To exit press CTRL+C')


def callback(ch, method, properties, body):

    con = _mysql.connect("localhost", "root", "coderslab", "rabbit")

    data = json.loads(body.decode("utf-8"))
    if data['action'] == 'set':
        con.query("INSERT INTO data (k, v) VALUES ('{}', '{}');".format(data['key'], data['value']))
        # cur.close()
        print(" [x] Added {} | {}".format(data["key"], data["value"]))
    elif data['action'] == 'get':
        con.query("SELECT v FROM data WHERE k={});".format(data['key']))
        for i in con:
            print(" [x] Value for {} is {}".format(data["key"], i))
        con.close()
    print(" [x] Done")
    con.close()
    ch.basic_ack(delivery_tag = method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(callback,
                      queue='task_queue')

channel.start_consuming()
