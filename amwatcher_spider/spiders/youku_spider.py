# -*- coding: utf-8 -*-

from datetime import datetime
from amwatcher_spider.spiders.base import BaseSpider, KeywordEscape
from scrapy import Spider, Request
import logging
logger = logging.getLogger(__name__)

PROXY_KEY = 'amwatcher:spider:login_proxy:%s'

class IqiyiSpider(BaseSpider):
    name = 'youku'
    search_pattern = 'http://www.soku.com/search_video/q_%(keyword)s'
    download_delay = 1
    handle_httpstatus_list = [302]
    
    def __init__(self, mode='prod', *args, **kwargs):
        super(IqiyiSpider, self).__init__(mode)
    
    def start_requests(self):
        self.start_timestamp = datetime.now()
        
        for kobj in self.mongo_keywords.find({'status': 'activated', '$or': [{ 'tags': '优酷'}, {'type': 'anime'}]}):
            search_words = [kobj['keyword']]
            if 'alias' in kobj:
                search_words.extend(kobj['alias'])
            for search_word in search_words:
                search_word_url = KeywordEscape(search_word)
                search_url = self.search_pattern % { 'keyword': search_word_url }
                feed = {
                    'source': 'youku',
                    'search_word': search_word,
                    'keyword_id': kobj['_id'],
                    'keyword_title': kobj['keyword'],
                }
                yield Request(url=search_url, meta={ 
                    'kobj': kobj, 
                    'feed': feed, 
                }, callback=self.parse_search)

    def parse_search(self, response):
        ''' 爬取优酷土豆
        
        @url http://www.soku.com/search_video/q_人渣的本愿
        '''
        meta = response.meta
        kobj = meta['kobj']
        
        logger.info('开始爬取番剧, URL: %s' % response.url)
        feed = dict(meta['feed'])
        
        # 剧集分组
        search_results = response.css('div.s_items ul.clearfix li')
        
        if not search_results:
            logger.info('[%s] 未找到番剧...' % kobj['keyword'])
        href_set = set()
        for series_item in search_results:
            series = series_item.css('a')
            title = series.css('::attr(_log_title)').extract_first()
            href = series.css('::attr(href)').extract_first()
            # 跳过预览
            if series.css('i.ico_partpre'):
                continue
            if title and href.startswith('http'):
                ep = series.css('span::text').extract_first()
                if href in href_set:
                    continue # 重复项
                href_set.add(href)
                epfeed = dict(feed)
                if series_item.css('.ico_partfree'):
                    epfeed['title'] = '%s(优酷VIP) ep%s' % (title, ep)
                else:
                    epfeed['title'] = '%s ep%s' % (title, ep)
                epfeed['href'] = href
                if kobj['type'] == 'anime': 
                    epfeed['type'] = 'bangumi'
                elif kobj['type'] == 'drama':
                    epfeed['type'] = 'drama'
                else:
                    continue
                epfeed['scrapy_time'] = datetime.now()
                epfeed['scrapy_start_time'] = self.start_timestamp
                epfeed['upload_time'] = epfeed['scrapy_time']
                epfeed['uploader'] = 'youku'
                exfeed = self.mongo_feeds.find_one({
                    'title': epfeed['title'],
                    'keyword_title': kobj['keyword'],
                    'source': epfeed['source'],
                })
                if exfeed:
                    logger.info('该条目已存在，略过...')
                else:
                    yield epfeed