# -*- coding: utf-8 -*-

import json
import time
import yaml
from pymongo import MongoClient
from redis import StrictRedis
from datetime import datetime, timedelta
from amwatcher_spider import settings
# from amwatcher_spider import rules
from scrapy import Spider
import logging
from logging.handlers import RotatingFileHandler

KEYWORD_COLLECTION = ''

class BaseSpider(Spider):    
    def __init__(self, mode='prod', *args, **kwargs):
        LOCAL_CONFIG = settings.local_config(mode)
        self.mongo_client = MongoClient(LOCAL_CONFIG['MONGO_URI'])
        self.mongo_db = self.mongo_client[LOCAL_CONFIG['MONGO_DATABASE']]
        
        self.redis_db = StrictRedis(
            host=LOCAL_CONFIG['REDIS_HOST'], 
            port=LOCAL_CONFIG['REDIS_PORT'], 
            password=LOCAL_CONFIG['REDIS_PASSWORD'],
            db=LOCAL_CONFIG['REDIS_DB']
        ) 
        self.mongo_keywords = self.mongo_db['keywords']
        self.mongo_logs = self.mongo_db['logs']
        self.mongo_feeds = self.mongo_db['feeds'] 
        self.mongo_accounts = self.mongo_db['accounts']
        self.start_timestamp = datetime.now()
        
        self.spider_logger = logging.getLogger(__name__)

        self.mode = mode