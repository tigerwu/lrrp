# -*- coding:utf-8 -*-

from flask import Flask
from flask import request, jsonify
import json
import redis

app = Flask(__name__)

rcon = redis.StrictRedis(host='localhost', db=1)
prodcons_queue = 'task:prodcons:queue'

@app.route('/', methods=['POST', 'GET'])
def index():
    return jsonify({'Hello':'World!!'})

@app.route('/mototrbo/start-ibeacon-report', methods=['POST'])
def start_ibeacon_report():
    jsondata = request.json
    print(jsondata)
    interval = jsondata['interval']
    radios = jsondata['radio-id']
    print(interval)
    print(radios)
    value = {}
    if interval == 0:
        #send stop request
        for radio in radios:
            print("send stop triggered_indoor reuqest to radio{}".format(radio))
            value['operate'] = 'stop'
            value['radioid'] = radio
            rcon.lpush(prodcons_queue, json.dumps(value))
    else:
        #send request
        for radio in radios:
            print("send triggered_indoor request to radio{}, interval {}s".format(radio, interval))
            value['operate'] = 'start'
            value['radioid'] = radio
            value['interval'] = interval
            rcon.lpush(prodcons_queue, json.dumps(value))
    return jsonify({'code':0, 'msg':'OK'})

