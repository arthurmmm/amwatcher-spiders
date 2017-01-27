# -*- coding: utf-8 -*-

import json
import time
import pymongo
from datetime import datetime, timedelta
from amwatcher_spider import dbsetting
from amwatcher_spider import settings
from amwatcher_spider import rules
from scrapy import Spider

class BaseSpider(Spider):
    def __init__(self):
        mongo_client = pymongo.MongoClient(dbsetting.MONGO_URI)
        mongo_db = mongo_client[dbsetting.MONGO_DATABASE]
        self.mongo_keywords = mongo_db[dbsetting.KEYWORD_COLLECTION]
        self.mongo_keywords_test = mongo_db[dbsetting.KEYWORD_TEST_COLLECTION]
        self.mongo_logs = mongo_db[dbsetting.LOG_COLLECTION]
        self.mongo_feeds = mongo_db[dbsetting.FEED_COLLECTION] 
        self.mongo_feeds_test = mongo_db[dbsetting.FEED_TEST_COLLECTION]          
        self.mongo_discards = mongo_db[dbsetting.DISCARD_COLLECTION]    
        self.start_timestamp = datetime.utcnow()
    
    def pipeRules(self, kobj, feed):
        router = settings.RULE_MAPPING
        source, type, title = feed['source'], feed['type'], feed['title']
        for rulename in router[source][type]:
            print('开始验证并执行规则: %s' % rulename)
            rule = getattr(rules, rulename)
            succ, feed = rule.tweak(kobj, feed)
            if not succ:
                print('验证规则[%s]失败: %s != %s' % (rulename, kobj['keyword'], title))
                # self.mongo_discards.insert({
                    # 'rulename': rulename,
                    # 'keyword': kobj,
                    # 'feed': feed,
                # })
                feed['valid'] = False
                feed['break_rule'] = rulename
                return feed
            print('成功通过规则: %s' % rulename)
        else:
            feed['valid'] = True
            return feed
            
    def HKT2UTC(self, t):
        return t - timedelta(hours=8)