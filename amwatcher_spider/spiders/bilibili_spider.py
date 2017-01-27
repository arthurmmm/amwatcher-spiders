# -*- coding: utf-8 -*-

import json
import time
from datetime import datetime
import pymongo
import re
from amwatcher_spider import dbsetting
from amwatcher_spider.spiders.base import BaseSpider
from random import random
from scrapy import Spider, Request
from scrapy.http import HtmlResponse
from collections import defaultdict
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
rfh = RotatingFileHandler('/var/tmp/amwatcher_bilibili_spider.log', maxBytes=5*1024*1024, backupCount=10)
logger.addHandler(rfh)

class BilibiliSpider(BaseSpider):
    name = 'bilibili'
    updrama_pattern = 'http://search.bilibili.com/ajax_api/video?keyword=%(keyword)s&page=1&order=pubdate&tids_1=11&tids_2=15'
    bangumi_pattern = 'http://search.bilibili.com/bangumi?keyword=%(keyword)s'
    bangumi_season_pattern = 'http://bangumi.bilibili.com/jsonp/seasoninfo/%(season_id)s.ver?callback=seasonListCallback&jsonp=jsonp'
    upbangumi_pattern = 'http://search.bilibili.com/ajax_api/video?keyword=%(keyword)s&page=1&order=pubdate&tids_1=13&tids_2=33'
    download_delay = 1
    
    handle_httpstatus_list = [302]
    
    def __init__(self, keyword=None, test=None, *args, **kwargs):
        self.keyword = keyword
        self.test = test
        super(BilibiliSpider, self).__init__()
    
    def start_requests(self):
        if self.test:
            logger.debug('## 测试模式！')
            self.mongo_keywords = self.mongo_keywords_test
            self.mongo_feeds = self.mongo_feeds_test
                    
        self.start_timestamp = datetime.now()
        self.mongo_logs.insert({
            'timestamp': self.start_timestamp,
            'event': 'start scrapy'
        })
        
        # 查询构造最近更新时间表
        res = self.mongo_feeds.aggregate([
            {
                '$sort': {'upload_time': -1},
            },
            {
                '$group': {
                    '_id': { 'keyword': '$keyword_id', 'source': '$source', 'type': '$type' },
                    'last_update_time': {'$first': '$upload_time'},
                    'last_update_feed': {'$first': '$title'},
                }
            }
        ])
        last_update_dict = defaultdict(lambda : defaultdict(lambda: defaultdict(lambda: (None, None))))
        for obj in res:
            logger.debug('%s %s %s => %s %s' % (obj['_id']['keyword'], obj['_id']['source'], obj['_id']['type'], obj['last_update_time'], obj['last_update_feed']))
            last_update_dict[obj['_id']['keyword']][obj['_id']['source']][obj['_id']['type']] = (obj['last_update_time'], obj['last_update_feed'])
        
        for kobj in self.mongo_keywords.find({'status': 'activated'}):
            keyword = kobj['keyword']
            if kobj['type'] == 'anime': 
                # 搜索官方版权番剧
                bangumi_url = self.bangumi_pattern % { 'keyword': keyword }
                feed = {
                    'source': 'bilibili',
                    'type': 'bangumi',
                    'keyword': kobj['keyword'],
                    'keyword_id': kobj['_id'],
                }
                yield Request(url=bangumi_url, meta={ 
                    'kobj': kobj, 
                    'feed': feed, 
                    'last_update': last_update_dict[kobj['_id']]['bilibili']['bangumi'],
                }, callback=self.parse_bangumi)
                # 搜索UP主上传番剧
                upbangumi_url = self.upbangumi_pattern % { 'keyword': keyword }
                feed = {
                    'source': 'bilibili',
                    'type': 'upbangumi',
                    'keyword': kobj['keyword'],
                    'keyword_id': kobj['_id'],
                }
                yield Request(url=upbangumi_url, meta={ 
                    'kobj': kobj, 
                    'feed': feed,
                    'last_update': last_update_dict[kobj['_id']]['bilibili']['upbangumi'],
                }, callback=self.parse_search_result)
            elif kobj['type'] == 'drama':
                updrama_url = self.updrama_pattern % { 'keyword': keyword }
                feed = {
                    'source': 'bilibili',
                    'type': 'updrama',
                    'keyword': kobj['keyword'],
                    'keyword_id': kobj['_id'],
                }
                yield Request(url=updrama_url, meta={ 
                    'kobj': kobj, 
                    'feed': feed,
                    'last_update': last_update_dict[kobj['_id']]['bilibili']['updrama'],
                }, callback=self.parse_search_result)

    def parse_bangumi(self, response):
        ''' 爬取B站官方番剧和UP主上传番剧
        
        @url http://search.bilibili.com/bangumi?keyword=暗芝居
        @kobj 暗芝居 anime bilibili bangumi
        '''
        meta = response.meta
        kobj = meta['kobj']
        
        logger.info('开始爬取官方番剧, URL: %s' % response.url)
        if 'proxy' in meta:
            logger.debug('使用代理: %s' % meta['proxy'])
        feed = dict(meta['feed'])
        
        search_results = response.css('.so-episode') 
        self.mongo_logs.insert({
            'timestamp': datetime.now(),
            'event': 'start parse_bangumi',
            'keyword': kobj['keyword'],
            'url': response.url,
        })
        
        if not search_results:
            logger.info('[%s] 未找到官方番剧...' % kobj['keyword'])
        for series in search_results.css('a.list.sm'):
            bangumi_url = 'http:' + series.xpath('./@href').extract_first()
            season_id = bangumi_url.split('/')[-1]
            season = series.xpath('./@title').extract_first()
            feed['season'] = season
            feed['type'] = 'bangumi'
            meta['feed'] = feed
            season_url = self.bangumi_season_pattern % {'season_id': season_id}
            yield Request(url=season_url, meta=meta, callback=self.parse_bangumi_detail)
            
        # feed = dict(meta['feed'])
        # feed['type'] = 'upbangumi'
        # meta['feed'] = feed
        # upbangumi_url = self.upbangumi_pattern % { "keyword": kobj['keyword'] }
        # yield Request(url=upbangumi_url, meta=meta, callback=self.parse_search_result)

    def parse_bangumi_detail(self, response):
        meta = response.meta
        kobj = meta['kobj']
        feed = dict(meta['feed'])
        
        logger.info('开始爬取番剧详情, URL: %s' % response.url)
        if 'proxy' in meta:
            logger.debug('使用代理: %s' % meta['proxy'])
        
        try:
            season = json.loads(
                re.match(
                    'seasonListCallback\((.*)\)', 
                    response.body_as_unicode()
                ).group(1)
            )['result']
        except AttributeError:
            logger.debug('### ' + response.body_as_unicode())
        
        for ep in season['episodes']:
            epfeed = dict(feed)
            epfeed['href'] = ep['webplay_url']
            epfeed['upload_time'] = datetime.strptime(
                ep['update_time'].split('.')[0], 
                '%Y-%m-%d %H:%M:%S'
            )
            # 检查更新时间(匹配更新时间)
            last_update_time, last_update_feed = meta['last_update']
            logger.info('上次更新：%s %s' % (last_update_time, last_update_feed))
            if last_update_time and last_update_time >= epfeed['upload_time']:
                logger.info('该条目已更新，略过...')
                continue
                
            epfeed['uploader'] = 'bilibili'
            epfeed['season'] = season['season_title']
            try:
                epfeed['episode'] = int(ep['index'])
            except Exception:
                logger.error('Invalid episode %s' % ep['index'])
                continue
            epfeed['title'] = ' '.join([season['title'], ep['index'], ep['index_title']])
            epfeed['scrapy_time'] = datetime.now()
            epfeed['scrapy_start_time'] = self.start_timestamp
            epfeed['tags'] = [ a['actor'] for a in season['actor'] ]
            epfeed['description'] = season['evaluate']
            epfeed = self.pipeRules(kobj, epfeed)
            if epfeed:
                yield epfeed
        
    def parse_search_result(self, response):
        ''' 爬取搜索内容的通用方法
        
        Test Case:
        
        Contract:
        @url "http://search.bilibili.com/ajax_api/video?keyword=谎言的战争&page=1&order=pubdate&tids_1=11&tids_2=15"
        @kobj 谎言的战争 drama bilibili bangumi
        '''
        meta = response.meta
        kobj = meta['kobj']
        
        logger.info('[%s]开始爬取搜索内容, URL: %s' % (kobj['keyword'], response.url))
        if 'proxy' in meta:
            logger.debug('使用代理: %s' % meta['proxy'])
        try:
            video_data = json.loads(response.body_as_unicode()) 
        except Exception as e:
            logger.error(response.body_as_unicode())
            logger.exception(e)
        if video_data['code'] == 1:
            logger.info('未找到相关视频！')
            return 
        total_page = video_data['numPages']
        cur_page = video_data['curPage']
        next_page = cur_page + 1
        video_html = video_data['html']
        video_response = HtmlResponse(url=response.url, body=video_data['html'].encode('utf-8'))
        self.mongo_logs.insert({
            'timestamp': datetime.now(),
            'event': 'start parse_updrama',
            'keyword': kobj['keyword'],
            'page': cur_page,
            'total_page': total_page,
            'url': response.url,
        })
        for video in video_response.css('li.video.matrix'):
            player_url = 'http:' + video.css('a::attr(href)').extract_first()
            title = video.css('.title::attr(title)').extract_first()
            update_date = video.css('span.so-icon.time::text').extract()[-1].replace('\t', '').replace('\n', '')
            update_date = datetime.strptime(update_date+' 23:59:59', '%Y-%m-%d %H:%M:%S')
            # 检查更新时间(匹配时间和番剧名字)
            last_update_time, last_update_feed = meta['last_update']
            logger.info('上次更新：%s %s' % (last_update_time, last_update_feed))
            if (last_update_feed and last_update_feed == title) or \
                (last_update_feed and last_update_time > update_date):
                logger.info('该条目已更新，结束搜索...')
                break # 搜索结果是按照时间排序的，因此直接结束本次搜索
                
            yield Request(url=player_url, meta=meta, callback=self.parse_player)
                
    def parse_player(self, response):
        meta = response.meta
        kobj = meta['kobj']
        feed = dict(meta['feed'])
        
        logger.info('开始爬取视频播放页, URL: %s' % response.url)
        if 'proxy' in meta:
            logger.debug('使用代理: %s' % meta['proxy'])
        
        feed['href'] = response.url
        feed['uploader'] = response.css('meta[name="author"]::attr(content)').extract_first()
        try:
            feed['upload_time'] = datetime.strptime(
                response.css('time[itemprop="startDate"] i::text').extract_first(), 
                '%Y-%m-%d %H:%M'
            )
        except TypeError as e:
            logger.info('视频尚在审核，略过')
            return
        feed['title'] = response.css('.v-title h1::text').extract_first()
        feed['scrapy_time'] = datetime.now()
        feed['scrapy_start_time'] = self.start_timestamp
        feed['tags'] = response.css('a.tag-val::text').extract()
        feed['description'] = response.css('div[id="v_desc"]::text').extract_first()
        logger.debug('处理前：%s' % feed)
        feed = self.pipeRules(kobj, feed)
        logger.debug('处理后：%s' % feed)
        if feed:
            yield feed
            
    def closed(self, reason):
        logger.info('完成！')