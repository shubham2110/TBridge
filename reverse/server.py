#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Time    : 2017/4/11
# @Author  : Twi1ight
import re
import sys
import socket
import select
import urllib
import threading , Queue

from bottle import request, run, route, error, abort
from copy import copy

from settings import route_to_transport, route_to_init, route_to_shutdown, md5digest
from settings import encrypt, decrypt, cookie_param_name, js_template_file, headers

connections={}
connectiond={}

@error(404)
@error(405)
def error404(err):
    return '404 Not Found.'


def invoke_service(data):
    sock.sendall(data)
    ret = ''
    while True:
        r, _, _ = select.select([sock], [], [], 0.1)
        if r:
            ret += sock.recv(4096)
            if len(ret) == 0:
                print('service sock closed')
                break
        else:
            print('service data length', len(ret))
            break
    return ret


@route('/%s' % route_to_transport)
def transport():
    verify_useragent()
    raw = urllib.unquote(request.get_cookie(cookie_param_name, ''))
    if not raw: return 'no client data found'
    data = decrypt(raw)
    ret = invoke_service(data)
    ciphertext = encrypt(ret)
    # obfuscate data to js file
    body = copy(js_template)
    ciphers = splitn(ciphertext, len(placeholder))
    for i in range(len(placeholder)):
        body = body.replace(placeholder[i], '"%s"' % ciphers[i], 1)
    return body + '//%s' % md5digest(ciphertext)


@route('/%s' % route_to_init)
def init():
    global sock
    verify_useragent()
    shutdown()
    try:
        sock = socket.socket()
        sock.connect((service_host, service_port))
    except Exception as e:
        return 'transport init failed: ', str(e)
    return 'transport inited.'


@route('/%s' % route_to_shutdown)
def shutdown():
    verify_useragent()
    try:
        sock.close()
    except:
        pass
    return 'transport stopped.'


def verify_useragent():
    if request.get_header('user-agent', '') != headers['User-Agent']:
        abort(404)


def get_template(filename):
    with open(filename) as f:
        template = f.read()
    return template


def splitn(s, n):
    l = len(s) / n if len(s) % n == 0 else len(s) / n + 1
    array = [s[i:i + l] for i in xrange(0, len(s), l)]
    for _ in range(n - len(array)):
        array.append('')
    return array


def argparse():
    if len(sys.argv) != 4:
        print ('usage: python server.py port-for-client service-host service-port')
        print ('e.g. for ssh: python server.py 8089 localhost 22')
        sys.exit()
    return int(sys.argv[1]), sys.argv[2], int(sys.argv[3])


def shutdown_client(client, address):
    while connections[address][1] > 0:
        continue
    connections[address]=[None, -1]
    connectiond[address]=None
    client.close()

def read_send_and_recv(address):
    while True:
        if connections[address][1] == -1 :
            return
        elif connections[address][1] == 0:
            continue
        elif connections[address][1] == 1 :
            print(connectiond[address].get())
            if connectiond[address].empty():
                connections[address][1]=0
# To be called on thread
def client_send_and_recv(client, address):
    connections[address]=[client,0]
    connectiond[address]=Queue.Queue()
    while True:
        try:
            buf = client.recv(data_fragment_size)
        except:
            #shutdown_client(client, address)
            break
        if len(buf) == 0 :
            #shutdown_client(client, address)
            break
        connectiond[address].put(buf)

def handle_clients(service_host, service_port):
    sock = socket.socket()
    sock.bind((service_host, service_port))
    sock.listen(1)
    
    while True:
        client, address = sock.accept()
        # Tobe called on thread
        x = threading.Thread(target=client_send_and_recv, args=(client,address))
        x.start()
	
        #client_send_and_recv(client, address)

def read_all_clients():
    while True:
        for each in connections.keys():
            threading.Thread(target=read_send_and_recv, args=(address,)).start()
        import time
        time.sleep(5)

if __name__ == '__main__':
    webserv_port, service_host, service_port = argparse()
    # webserv_port, service_host, service_port = 8089, 'localhost', 22
    handle_clients(service_host, service_port)
    threading.Thread(target=read_all_clients).start()
    #sock = None
    #js_template = get_template(js_template_file)
    #placeholder = re.findall('(".*?")', js_template)
    #run(server='cherrypy', host='0.0.0.0', port=webserv_port, debug='debug')
    
