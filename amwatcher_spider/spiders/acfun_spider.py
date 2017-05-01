# -*- coding: utf-8 -*-

import json
from datetime import datetime
import re
from amwatcher_spider.spiders.base import BaseSpider, KeywordEscape
from scrapy import Spider, Request
import logging
logger = logging.getLogger(__name__)

PROXY_KEY = 'amwatcher:spider:login_proxy:%s'


class AcfunSpider(BaseSpider):
    name = 'acfun'
    updrama_pattern = 'http://search.aixifan.com/search?q=%(keyword)s&isArticle=1&cd=1&sys_name=pc&format=system.searchResult&pageSize=20&pageNo=1&type=2&isWeb=1&sortField=releaseDate&parentChannelId=68&channelId=162'
    upvariety_pattern = 'http://search.aixifan.com/search?q=%(keyword)s&isArticle=1&cd=1&sys_name=pc&format=system.searchResult&pageSize=20&pageNo=1&type=2&isWeb=1&sortField=releaseDate&parentChannelId=60&channelId=98'
    video_pattern = 'http://www.acfun.tv/v/%s'
    download_delay = 2
    handle_httpstatus_list = [302]
    use_proxy = False
    
    def __init__(self, mode='prod', *args, **kwargs):
        super(AcfunSpider, self).__init__(mode)
    
    def start_requests(self):
        self.start_timestamp = datetime.now()
        
        for kobj in self.mongo_keywords.find({'status': 'activated', '$or': [
            {'tags': 'AcFun'},
            {'type': 'drama'},
            {'type': 'variety'},
        ]}):
            search_words = [kobj['keyword']]
            if 'alias' in kobj:
                search_words.extend(kobj['alias'])
            for search_word in search_words:
                search_word_url = KeywordEscape(search_word)
                if kobj['type'] == 'drama':
                    # 搜索UP主上传番剧
                    updrama_url = self.updrama_pattern % { 'keyword': search_word_url }
                    feed = {
                        'source': 'acfun',
                        'type': 'updrama',
                        'search_word': search_word,
                        'keyword_id': kobj['_id'],
                        'keyword_title': kobj['keyword'],
                    }
                    yield Request(url=updrama_url, meta={
                        'kobj': kobj, 
                        'feed': feed,
                    }, callback=self.parse_search_result)
                elif kobj['type'] == 'variety':
                    upvariety_url = self.upvariety_pattern % { 'keyword': search_word_url }
                    feed = {
                        'source': 'acfun',
                        'type': 'upvariety',
                        'search_word': search_word,
                        'keyword_id': kobj['_id'],
                        'keyword_title': kobj['keyword'],
                    }
                    yield Request(url=upvariety_url, meta={
                        'kobj': kobj,
                        'feed': feed,
                    }, callback=self.parse_search_result)
                else:
                    logger.warning('发现不合法关键字')

    def parse_search_result(self, response):
        ''' 爬取搜索结果
        '''
        meta = response.meta
        kobj = meta['kobj']
        feed = dict(meta['feed'])
        
        logger.info('搜索URL: %s' % response.url)
        resources = []
        try:
            resources = json.loads(
                re.match(
                    'system\.searchResult=(.*)',
                    response.body_as_unicode()
                ).group(1)
            )['data']['page']['list']
        except AttributeError as e:
            logger.error(e)
            logger.debug('### ' + response.body_as_unicode())
        
        for ep in resources:
            epfeed = dict(feed)
            epfeed['href'] = self.video_pattern % ep['contentId']
            epfeed['upload_time'] = datetime.fromtimestamp(ep['releaseDate'] / 1000)
            epfeed['uploader'] = ep['username']
            epfeed['title'] = ep['title']
            epfeed['scrapy_time'] = datetime.now()
            epfeed['scrapy_start_time'] = self.start_timestamp
            epfeed['tags'] = ep['tags']
            epfeed['description'] = ep['description']
            
            # 检查是否存在
            exfeed = self.mongo_feeds.find_one({
                'title': epfeed['title'],
                'keyword_title': kobj['keyword'],
                'source': epfeed['source'],
            })
            if exfeed:
                logger.info('该条目已存在，略过...')
            elif epfeed:
                yield epfeed
