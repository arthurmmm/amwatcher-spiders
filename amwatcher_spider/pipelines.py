# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo
import json
import amwatcher_spider.dbsetting as dbsetting

class AmwatcherSpiderPipeline(object):
    def process_item(self, item, spider):
        return item

class MongoDBPipeline(object):
    
    # collection = 'rawfeeds_test'
    
    def open_sipder(self, spider):
        self.client = pymongo.MongoClient(dbsetting.MONGO_URI)
        self.db = self.client[dbsetting.MONGO_DATABASE]
        
    def close_sipder(self, spider):
        self.client.close()
        
    def process_item(self, item, spider):
        self.client = pymongo.MongoClient(dbsetting.MONGO_URI)
        self.db = self.client[dbsetting.MONGO_DATABASE]
        
        if hasattr(spider, 'test') and spider.test:
            self.db[dbsetting.FEED_TEST_COLLECTION].insert(dict(item))
        else:
            self.db[dbsetting.FEED_COLLECTION].insert(dict(item))
        return item