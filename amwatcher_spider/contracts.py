# -*- coding: utf-8 -*-

import scrapy
import json
import pymongo
from amwatcher_spider import dbsetting
from scrapy.contracts import Contract
from scrapy.exceptions import ContractFail

class KobjContract(Contract): 
    name = 'kobj'
    
    def adjust_request_args(self, args):
        # return args
        mongo_client = pymongo.MongoClient(dbsetting.MONGO_URI)
        mongo_db = mongo_client[dbsetting.MONGO_DATABASE]
        mongo_keywords = mongo_db[dbsetting.KEYWORD_COLLECTION]
        (keyword, type, source, feedtype) = self.args
        kobj = mongo_keywords.find_one({
            'keyword': keyword,
            'type': type,
        })
        feed = {
            'source': source,
            'type': feedtype,
            'keyword': kobj['keyword'],
            'keyword_id': kobj['_id'],
        }
        args['meta'] = { 'kobj': kobj, 'feed': feed }
        print('测试目标：%s' % kobj)
        return args
        
    def post_process(self, output):
        if type(output).__name__ == 'dict':
            print(json.dumps(output, indent=4))
        else:
            print(output)