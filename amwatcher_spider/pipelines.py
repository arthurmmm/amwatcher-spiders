# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from pymongo import MongoClient
import json
from amwatcher_spider import settings
import yaml
import logging

class AmwatcherSpiderPipeline(object):
    def process_item(self, item, spider):
        return item

class MongoDBPipeline(object):
    
    def open_sipder(self, spider):
        LOCAL_CONFIG = settings.local_config(spider.mode)
        self.client = MongoClient(LOCAL_CONFIG['MONGO_URI'])
        self.db = self.client[LOCAL_CONFIG['MONGO_DATABASE']]
        
    def close_sipder(self, spider):
        self.client.close()
        
    def process_item(self, item, spider):
        LOCAL_CONFIG = settings.local_config(spider.mode)
        self.client = MongoClient(LOCAL_CONFIG['MONGO_URI'])
        self.db = self.client[LOCAL_CONFIG['MONGO_DATABASE']]

        self.db['feeds'].insert(dict(item))
        return item