#!/usr/bin/env python
import pika
import sys
import json

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='task_queue', durable=True)

part_1 = ' '.join(sys.argv[1:2])
part_2 = ' '.join(sys.argv[2:])
channel.basic_publish(exchange='',
                      routing_key='task_queue',
                      body=json.dumps({'action': 'set', 'key': part_1, 'value': part_2}),
                      properties=pika.BasicProperties(
                         delivery_mode = 2, # make message persistent
                      ))
print(" [x] Request sent. key: {} value: {}".format(part_1, part_2))
connection.close()
