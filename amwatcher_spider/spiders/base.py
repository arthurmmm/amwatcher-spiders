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
        # 匹配force_include规则
        if 'force_include' in kobj:
            for fi_item in kobj['force_include']:
                fi_name = fi_item['name']
                fi_kobj = fi_item['kobj']
                fi_rules = fi_item['rules']
                self.spider_logger.info('发现强规则：%s' % fi_name)
                # 若完全匹配某个force_include规则，返回认证成功
                for rulename in fi_rules:
                    self.spider_logger.info('开始验证并执行规则: %s，强制匹配对象：%s' % (rulename, fi_kobj['keyword']))
                    rule = getattr(rules, rulename)
                    succ, feed = rule.tweak(fi_kobj, feed)
                    if not succ:
                        self.spider_logger.info('强规则%s匹配失败..' % fi_name)
                        break
                else:
                    self.spider_logger.info('强规则%s匹配成功!' % fi_name)
                    feed['valid'] = True
                    feed['force_include'] = fi_name
                    return feed
                    
        # 匹配默认规则
        for rulename in router[source][type]:
            self.spider_logger.info('开始匹配规则: %s' % rulename)
            rule = getattr(rules, rulename)
            succ, feed = rule.tweak(kobj, feed)
            if not succ:
                self.spider_logger.info('验证规则[%s]失败: %s != %s' % (rulename, kobj['keyword'], title))
                feed['valid'] = False
                feed['break_rule'] = rulename
                return feed
            self.spider_logger.info('成功通过规则: %s' % rulename)
            
        # TODO - 匹配force_exclude规则
        feed['valid'] = True
        return feed