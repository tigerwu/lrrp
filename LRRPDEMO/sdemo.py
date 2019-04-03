# -*- coding: utf-8 -*-

import time
import socket
import schedule
import redis
import json
import threading
import http.client

rcon = redis.StrictRedis(host='localhost', db=1)
prodcons_queue = 'task:prodcons:queue'

def printbytearray(bytes):
    for b in bytes:
        print('0x{:x}'.format(b), end=' ')
    pass

def get_ibeacon_data_from_bytes(bytes):
    beaconcount = bytes[0]
    print('beacon count:{}'.format(beaconcount))
    if beaconcount > 0:
        datas = []
        startindex = 1
        for i in range(beaconcount):
            print('i:{}'.format(i))
            data = {}
            startindex = 1 + (24 * i)
            endindex = startindex + 24
            print('start:{}, end:{}'.format(startindex,endindex))
            item = bytes[startindex:endindex]
            print(item)
            uuid = ''
            j = 0
            for j in range(16):
                uuid = uuid + '{0:0>2X}'.format(item[j])
            data['uuid'] = uuid
            print('major item16:{}, item17:{}'.format(item[16], item[17]))
            data['major'] = 256*item[16]+item[17]
            print('minor item18:{}, item19:{}'.format(item[18], item[19]))
            data['minor'] = 256*item[18]+item[19]
            data['txpower'] = item[20]
            data['rssi'] = item[21]-0xff
            data['timestamp'] = 256*item[22]+item[23]
            datas.append(data)
        return datas
    else:
        return None




def stop_answer_indoor(ds, radioip):
    sendbuffer = bytes([0x11,0x07,0x22,0x04,0x0c,0x00,0x00,0x0f,0x38])
    radiohost = ('12.0.0.15',4001)
    count = ds.sendto(sendbuffer, radiohost)
    print('\nsend {} bytes'.format(count))
    #print(sendbuffer)
    printbytearray(sendbuffer)

def immediate_indoor(ds, radioip, interval):
    #sendbuffer = bytes([0x05,0x09,0x22,0x04,0x0C,0x00,0x00,0x0F,0x6c,0x7c,0x03])
    sendbuffer = [0x05,0x09,0x22,0x04,0x6c,0x7c]
    sendbuffer.insert(4, radioip[3])
    sendbuffer.insert(4, radioip[2])
    sendbuffer.insert(4, radioip[1])
    sendbuffer.insert(4, radioip[0])
    sendbuffer.insert(10, interval)
    sendbuffer = bytes(sendbuffer)
    printbytearray(sendbuffer)

    radioipstr = '{}.{}.{}.{}'.format(radioip[0],radioip[1],radioip[2],radioip[3])
    print(radioipstr)

    radiohost = (radioipstr,4001)
    count = ds.sendto(sendbuffer, radiohost)
    print('\nsend {} bytes'.format(count))
    
def stop_req_indoor(ds, radioip):
    #sendbuffer = bytes([0x0F,0x06,0x22,0x04,0x0c,0x00,0x00,0x0f])
    sendbuffer = [0x0F,0x06,0x22,0x04]
    sendbuffer.insert(4, radioip[3])
    sendbuffer.insert(4, radioip[2])
    sendbuffer.insert(4, radioip[1])
    sendbuffer.insert(4, radioip[0])
    sendbuffer = bytes(sendbuffer)
    printbytearray(sendbuffer)

    radioipstr = '{}.{}.{}.{}'.format(radioip[0],radioip[1],radioip[2],radioip[3])
    print(radioipstr)

    radiohost = (radioipstr,4001)
    count = ds.sendto(sendbuffer, radiohost)
    print('\nsend {} bytes'.format(count))

def triggered_indoor(ds, radioip, interval):
    #sendbuffer = bytes([0x09,0x0c,0x22,0x04,0x0C,0x00,0x00,0x0F,0x6c,0x7c,0x03,0x34,0x31,0x1E])
    sendbuffer = [0x09,0x0c,0x22,0x04,0x6c,0x7c,0x34,0x31,0x1E]
    sendbuffer.insert(4, radioip[3])
    sendbuffer.insert(4, radioip[2])
    sendbuffer.insert(4, radioip[1])
    sendbuffer.insert(4, radioip[0])
    sendbuffer.insert(10, interval)
    sendbuffer = bytes(sendbuffer)
    printbytearray(sendbuffer)

    radioipstr = '{}.{}.{}.{}'.format(radioip[0],radioip[1],radioip[2],radioip[3])
    print(radioipstr)

    radiohost = (radioipstr,4001)
    count = ds.sendto(sendbuffer, radiohost)
    print('\nsend {} bytes'.format(count))

def send_triggered_indoor_to_radio(sock):
    print("\nsend_triggered_indoor_to_radio working...{}".format(threading.activeCount()))
    llen = rcon.llen(prodcons_queue)
    for index in range(llen):
        operatestr = rcon.rpop(prodcons_queue)
        operate = json.loads(operatestr)
        radioip = [12,0,0,operate['radioid']]
        print(radioip)
        if operate['operate'] == 'stop':
            stop_req_indoor(sock, radioip)
            pass
        elif operate['operate'] == 'start':
            #triggered_indoor(sock, radioip, operate['interval'])
            immediate_indoor(sock, radioip, operate['interval'])
            pass
    time.sleep(1)


def rev_from_radio(ds):
    while True:
        print("\nrev_from_radio working...{}".format(threading.activeCount()))
        data, addr = ds.recvfrom(4001)
        print('rev_from_radio[{}]'.format(addr))
        printbytearray(data)

        if data[0] ==0x07 and data[1] == 0x51: #Immediate Indoor Location Report
            radioid = data[7]
            beacondata = get_ibeacon_data_from_bytes(data[10:])
            print('radioid: {}'.format(radioid))
            print(beacondata)
            commit_beacon(radioid, beacondata)
        time.sleep(1)

def commit_beacon(radioid, beacondata):
    connection = http.client.HTTPConnection('127.0.0.1:5000')
    headers = {'Content-type': 'application/json'}
    data = {'radioid':radioid, 'ibeacons':beacondata}
    print(data)
    json_data = json.dumps(data)
    print(json_data)
    connection.request('POST', '/mototrbo/scan-result', json_data, headers)
    response = connection.getresponse()
    print(response.read().decode('utf-8'))


def run_threaded(job_func, sock):
     job_thread = threading.Thread(target=job_func, args=(sock,))
     job_thread.start()

def main():
    HostPort = ('192.168.10.2',4001)
    #HostPort = ('0.0.0.0',4001)
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) #创建UDP套接字
    sock.bind(HostPort) #服务器端绑定端口

    run_threaded(rev_from_radio, sock)
    schedule.every(3).seconds.do(run_threaded, send_triggered_indoor_to_radio, sock)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # execute only if run as a script
    main()

    # bytes=[0x7,0x51,0x22,0x4,0xc,0x0,0x0,0xf,0x73,0x77,
    # 0x3,0xfd,0xa5,0x6,0x93,0xa4,0xe2,0x4f,0xb1,0xaf,0xcf,0xc6,0xeb,0x7,0x64,
    # 0x78,0x25,0x27,0x12,0x14,0x51,0xc5,0xca,0x3,0x87,0xfd,0xa5,0x6,0x93,0xa4,0xe2,
    # 0x4f,0xb1,0xaf,0xcf,0xc6,0xeb,0x7,0x64,0x78,0x25,0x27,0x12,0x14,0x52,0xc2,0xce,
    # 0x3,0x87,0xfd,0xa5,0x6,0x93,0xa4,0xe2,0x4f,0xb1,0xaf,0xcf,0xc6,0xeb,0x7,0x64,
    # 0x78,0x25,0x27,0x12,0x14,0x51,0xc5,0xce,0x3,0x86]
    
    # result = get_ibeacon_data_from_bytes(bytes[10:])
    # print(result)
