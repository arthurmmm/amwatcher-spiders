# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/spider-middleware.html

import random
from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware 
from scrapy.downloadermiddlewares.retry import RetryMiddleware  
from scrapy.exceptions import NotConfigured  
import os
import yaml
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from twisted.web._newclient import ResponseNeverReceived
from twisted.internet.error import TimeoutError, ConnectionRefusedError, ConnectError
# from . import dbsetting
from amwatcher_spider import settings
from redis import StrictRedis

logger = logging.getLogger(__name__)

PROXY_SET = 'hq-proxies:proxy_pool'
ACCOUNT_SET = 'amwatcher:spider:%s:accounts'
PROXY_KEY = 'amwatcher:spider:login_proxy:%s'

class AmwatcherUserAgentMiddleware(UserAgentMiddleware):
    
    #the default user_agent_list composes chrome,I E,firefox,Mozilla,opera,netscape
    #for more user agent strings,you can find it in http://www.useragentstring.com/pages/useragentstring.php
    user_agent_list = [
        # "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 "
        # "(KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        # "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 "
        # "(KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
        # "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 "
        # "(KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        # "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 "
        # "(KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        # "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 "
        # "(KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        # "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 "
        # "(KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
        # "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 "
        # "(KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        # "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        # "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        # "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        # "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        # "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        # "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        # "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        # "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        # "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 "
        # "(KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        # "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 "
        # "(KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        # "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 "
        # "(KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36"
    ]

    def __init__(self, user_agent=''):  
        self.user_agent = user_agent  
  
    def process_request(self, request, spider):  
        logger.debug('使用代理：%s, 使用COOKIE：%s' % (request.meta['proxy'], request.cookies))
        ua = random.choice(self.user_agent_list)
        if ua:
            request.headers.setdefault('User-Agent', ua)
            
class DynamicProxyMiddleware(object):
    

    def process_request(self, request, spider):
        '''
        将request设置为使用代理
        '''
        LOCAL_CONFIG = settings.local_config(spider.mode)
        redis_db = StrictRedis(
            host=LOCAL_CONFIG['REDIS_HOST'], 
            port=LOCAL_CONFIG['REDIS_PORT'], 
            password=LOCAL_CONFIG['REDIS_PASSWORD'],
            db=LOCAL_CONFIG['REDIS_DB']
        ) 
        if hasattr(spider, 'spider_logger'):
            logger = spider.spider_logger
        
        # 访问REDIS获得一个随机账号
        account = redis_db.srandmember(ACCOUNT_SET % spider.name)
        account = json.loads(account.decode('utf-8'))
        # 访问REDIS查询是否有对应代理
        proxy = redis_db.get(PROXY_KEY % account['key'])
        # 查询PROXY_SET看看代理是否有效
        if proxy and redis_db.sismember(PROXY_SET, proxy):
            pass
        else:
            logger.debug('帐号[%s]代理已失效或不存在，重新绑定代理...' % account['key'])
            proxy = redis_db.srandmember(PROXY_SET)
            redis_db.set(PROXY_KEY % account['key'], proxy)
        proxy = proxy.decode('utf-8')
            
        logger.debug('使用帐号[%s]代理[%s]访问[%s]' % (account['key'], proxy, request.url))
        request.meta['proxy'] = proxy
        request.cookies = account['cookies']
        
        