#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import os
import requests
from requests.utils import dict_from_cookiejar
import rsa
import json
import base64

USERNAME = 'arthurreg@outlook.com'
PASSWORD = 'Dianjugzpt01'

def login(username, password):
    
    # step0 - start session for cookies
    session = requests.Session()
    session.get('https://passport.bilibili.com/ajax/miniLogin/minilogin')
    
    # step1 - get captcha
    while True:
        res = session.get('https://passport.bilibili.com/captcha')
        with open('/root/git/nginx-sh1/html/captcha.png', 'wb') as f:
            f.write(res.content)
        print('View captcha from this url: http://118.89.107.68/captcha.png')
        captcha = input('Please type captcha, type "retry" if need refresh: ')
        if captcha == 'retry':
            continue
        else:
            break
        
    # step2 - get HASH and RSA pubkey
    print('get HASH and RSA pubkey')
    res = session.get('https://passport.bilibili.com/login?act=getkey')
    hash, pubkey = res.json()['hash'], res.json()['key']
    print('hash: %s, pubkey: %s' % (hash, pubkey))
    
    # step3 - encrypt password (RSA+base64)
    pwd = hash + password
    pwd = pwd.encode('utf-8')
    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(pubkey.encode('utf-8'))
    pwd = rsa.encrypt(pwd, pubkey)
    print('pwd[RSA]: %s' % (pwd))
    pwd = base64.b64encode(pwd)
    print('pwd[BASE64]: %s' % (pwd))
    
    # step4 - login
    res = session.post('https://passport.bilibili.com/ajax/miniLogin/login', data={
        'userid': username,
        'pwd': pwd,
        'captcha': captcha,
        'keep': 1,
    })
    
    print(res.text)
    cookie = dict_from_cookiejar(session.cookies)
    print(cookie)
    with open('/var/tmp/cookies.json', 'w') as f:
        f.write(json.dumps(cookie))
    
login(USERNAME, PASSWORD)