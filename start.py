#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import logging.config
import argparse
from amwatcher_spider import settings
from pymongo import MongoClient, ASCENDING, DESCENDING
from redis import StrictRedis
from datetime import datetime
from analyzer import analyzer

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': '%(thread)d %(asctime)s %(levelname)s %(module)s/%(lineno)d: %(message)s',
        },
    },
    'handlers':{
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG'
        },
        '__main__': {
            'propagate': False,
            'handlers': ['console'],
            'level': 'DEBUG'
        },
    },
}
    
def main(args):
    if args.crawl:
        if args.env == 'test':
            os.system('scrapy crawl bilibili -a mode=test')
        else:
            os.system('scrapy crawl bilibili')
    if args.analyze:
        # 逐条分析采集数据
        if args.analyze_all:
            feeds = mongo_feeds.find({}) 
        else:
            feeds = mongo_feeds.find({'analyzed': {'$exists': False}})

        for feed in feeds:
            condition = mongo_keywords.find_one({'_id': feed['keyword_id']})
            feed = analyzer.analyze(feed, condition)
            mongo_feeds.find_one_and_replace({'_id': feed['_id']}, feed)
    if args.series:
        # 整体分析采集数据并构造剧集库
        kobjs = mongo_keywords.find({'status': 'activated'})
        for kobj in kobjs:
            # 按剧集组织feed并记录到series collection中
            logger.info('开始分析：%s' % kobj['keyword'])
            feeds = mongo_feeds.find({
                'keyword_id': kobj['_id'], 
                'break_rules': {'$exists': False},
            }).sort('upload_time', DESCENDING)
            vfeed_count = feeds.count()
            analyzer.timeline(feeds, mongo_series)
            # 在keyword中记录有效feed数
            feed_count = mongo_feeds.find({ 'keyword_id': kobj['_id'] }).count()
            mongo_keywords.update({'_id': kobj['_id']}, {
                "$set": {
                    'valid_feed_count': vfeed_count,
                    'feed_count': feed_count,
                }
            })
        # 计算并保存feeds_first_upload
        for ep in mongo_series.find({}):
            first_upload_time = min(ep['feeds_upload_time'])
            logger.debug(first_upload_time)
            mongo_series.find_one_and_update(
                {'_id': ep['_id']},
                {
                    '$set': {
                        'first_upload_time': first_upload_time,
                    },
                },
            )
        # 检查每个keyword最后一个有效feed的upload_time，并根据EXPIRE
        logger.info('时间线分析完成！')
    if args.expire:
        new_expire_count = analyzer.expire(mongo_feeds, mongo_keywords)
        logger.info('检查关键字失效完成，新增失效关键字%s个' % new_expire_count)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', default='prod', metavar='PORT')
    parser.add_argument('-c', '--crawl', default=False, action='store_true')
    parser.add_argument('-a', '--analyze', default=False, action='store_true')
    parser.add_argument('--analyze_all', default=False, action='store_true')
    parser.add_argument('-s', '--series', default=False, action='store_true')
    parser.add_argument('-e', '--expire', default=False, action='store_true')
    # parser.add_argument('-r', '--reset', default='prod', metavar='PORT')
    args = parser.parse_args()
    
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('__main__')
    LOCAL_CONFIG = settings.local_config(args.env)
    mongo_client = MongoClient(LOCAL_CONFIG['MONGO_URI'])
    mongo_db = mongo_client[LOCAL_CONFIG['MONGO_DATABASE']]

    redis_db = StrictRedis(
        host=LOCAL_CONFIG['REDIS_HOST'], 
        port=LOCAL_CONFIG['REDIS_PORT'], 
        password=LOCAL_CONFIG['REDIS_PASSWORD'],
        db=LOCAL_CONFIG['REDIS_DB']
    ) 
    mongo_keywords = mongo_db['keywords']
    mongo_logs = mongo_db['logs']
    mongo_feeds = mongo_db['feeds'] 
    mongo_accounts = mongo_db['accounts']
    mongo_series = mongo_db['series']
    main(args)




