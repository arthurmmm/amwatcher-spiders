# -*- coding: utf-8 -*-

import json
import time
from datetime import datetime
import pymongo
import re
from amwatcher_spider.spiders.base import BaseSpider
from random import random
from scrapy import Spider, Request
from scrapy.http import HtmlResponse
from collections import defaultdict
import logging
import requests
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

BILIBILI_ACCOUNT_SET = 'amwatcher:spider:bilibili:accounts'
PROXY_KEY = 'amwatcher:spider:login_proxy:%s'

class BilibiliSpider(BaseSpider):
    name = 'bilibili'
    updrama_pattern = 'http://search.bilibili.com/ajax_api/video?keyword=%(keyword)s&page=1&order=pubdate&tids_1=11&tids_2=15'
    bangumi_pattern = 'http://search.bilibili.com/bangumi?keyword=%(keyword)s'
    bangumi_season_pattern = 'http://bangumi.bilibili.com/jsonp/seasoninfo/%(season_id)s.ver?callback=seasonListCallback&jsonp=jsonp'
    upbangumi_pattern = 'http://search.bilibili.com/ajax_api/video?keyword=%(keyword)s&page=1&order=pubdate&tids_1=13&tids_2=33'
    upvariety_pattern = 'http://search.bilibili.com/ajax_api/video?keyword=%(keyword)s&page=1&order=pubdate&tids_1=5&tids_2=71'
    download_delay = 0.5
    handle_httpstatus_list = [302]
    
    def __init__(self, mode='prod', *args, **kwargs):
        super(BilibiliSpider, self).__init__(mode)
    
    def start_requests(self):
        self.start_timestamp = datetime.now()
        
        logger.debug('检查并缓存帐号登陆信息')
        self.redis_db.delete(BILIBILI_ACCOUNT_SET) # 清空并重构帐号池
        pkeys = self.redis_db.keys(PROXY_KEY % '*')
        if pkeys:
            self.redis_db.delete(*pkeys) # 清空并重构帐号-代理映射
        accounts = self.mongo_accounts.find({'source': 'bilibili'})
        for account in accounts:
            logger.debug(account)
            login_info = { 
                'key': account['key'], 
                'cookies': account['cookies'] 
            }
            res = requests.get('http://space.bilibili.com', cookies=account['cookies'])
            regex = re.search('<title>(.+)的个人空间', res.text)
            if regex:
                username = regex.group(1)
                logging.info('用户%s登陆成功！' % username)
            else:
                username = account['username']
                logging.info('用户%s登陆失败！' % username)
                logging.error(res.text)
                
            self.redis_db.sadd(BILIBILI_ACCOUNT_SET, json.dumps(login_info))
        
        for kobj in self.mongo_keywords.find({'status': 'activated'}):
            # keyword = 
            search_words = [kobj['keyword']]
            if 'alias' in kobj:
                search_words.extend(kobj['alias'])
            for search_word in search_words:
                if kobj['type'] == 'anime': 
                    # 搜索官方版权番剧
                    bangumi_url = self.bangumi_pattern % { 'keyword': search_word }
                    feed = {
                        'source': 'bilibili',
                        'type': 'bangumi',
                        'search_word': search_word,
                        'keyword_id': kobj['_id'],
                        'keyword_title': kobj['keyword'],
                    }
                    yield Request(url=bangumi_url, meta={ 
                        'kobj': kobj, 
                        'feed': feed, 
                    }, callback=self.parse_bangumi)
                    # 搜索UP主上传番剧
                    upbangumi_url = self.upbangumi_pattern % { 'keyword': search_word }
                    feed = {
                        'source': 'bilibili',
                        'type': 'upbangumi',
                        'search_word': search_word,
                        'keyword_id': kobj['_id'],
                        'keyword_title': kobj['keyword'],
                    }
                    yield Request(url=upbangumi_url, meta={ 
                        'kobj': kobj, 
                        'feed': feed,
                    }, callback=self.parse_search_result)
                elif kobj['type'] == 'drama':
                    updrama_url = self.updrama_pattern % { 'keyword': search_word }
                    feed = {
                        'source': 'bilibili',
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
                    upvariety_url = self.upvariety_pattern % { 'keyword': search_word }
                    feed = {
                        'source': 'bilibili',
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

    def parse_bangumi(self, response):
        ''' 爬取B站官方番剧和UP主上传番剧
        
        @url http://search.bilibili.com/bangumi?keyword=暗芝居
        @kobj 暗芝居 anime bilibili bangumi
        '''
        meta = response.meta
        kobj = meta['kobj']
        
        logger.info('开始爬取官方番剧, URL: %s' % response.url)
        feed = dict(meta['feed'])
        
        search_results = response.css('.so-episode') 
        
        if not search_results:
            logger.info('[%s] 未找到官方番剧...' % kobj['keyword'])
        for series in search_results.css('a.list.sm'):
            bangumi_url = 'http:' + series.xpath('./@href').extract_first()
            season_id = bangumi_url.split('/')[-1]
            season = series.xpath('./@title').extract_first()
            feed['season'] = [season]
            feed['type'] = 'bangumi'
            meta['feed'] = feed
            season_url = self.bangumi_season_pattern % {'season_id': season_id}
            yield Request(url=season_url, meta=meta, callback=self.parse_bangumi_detail)

    def parse_bangumi_detail(self, response):
        meta = response.meta
        kobj = meta['kobj']
        feed = dict(meta['feed'])
        
        logger.info('开始爬取番剧详情, URL: %s' % response.url)
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
                
            epfeed['uploader'] = 'bilibili'
            epfeed['season'] = [season['season_title']]
            try:
                epfeed['episode'] = [int(ep['index'])]
            except Exception:
                logger.error('Invalid episode %s' % ep['index'])
                continue
            epfeed['title'] = ' '.join([season['title'], ep['index'], ep['index_title']])
            epfeed['scrapy_time'] = datetime.now()
            epfeed['scrapy_start_time'] = self.start_timestamp
            epfeed['tags'] = [ a['actor'] for a in season['actor'] ]
            epfeed['description'] = season['evaluate']
            
            # 检查是否存在
            exfeed = self.mongo_feeds.find_one({
                'title': epfeed['title'],
                'href': epfeed['href'],
            })
            if exfeed:
                logger.info('该条目已存在，略过...')
            elif epfeed:
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
        try:
            video_data = json.loads(response.body_as_unicode()) 
        except Exception as e:
            logger.exception(e)
        if video_data['code'] == 1:
            logger.info('未找到相关视频！')
            return 
        total_page = video_data['numPages']
        cur_page = video_data['curPage']
        next_page = cur_page + 1
        video_html = video_data['html']
        video_response = HtmlResponse(url=response.url, body=video_data['html'].encode('utf-8'))
        for video in video_response.css('li.video'):
            player_url = 'http:' + video.css('a::attr(href)').extract_first()
            title = video.css('.title::attr(title)').extract_first()
            update_date = video.css('span.so-icon.time::text').extract()[-1].replace('\t', '').replace('\n', '')
            update_date = datetime.strptime(update_date+' 23:59:59', '%Y-%m-%d %H:%M:%S')
            if not player_url.endswith('/'):
                player_url += '/'
            meta['feed'].update({
                'href': player_url
            })
            
            # 检查是否存在
            exfeed = self.mongo_feeds.find_one({
                'title': title,
                'href': player_url,
            })
            if exfeed:
                logger.info('该条目已存在，略过...')
            else:
                yield Request(url=player_url, meta=meta, callback=self.parse_player)
                
    def parse_player(self, response):
        meta = response.meta
        kobj = meta['kobj']
        feed = dict(meta['feed'])
        
        logger.info('开始爬取视频播放页, URL: %s' % response.url)
        
        # feed['href'] = response.url
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
        # 搜索分P视频
        feed['pvideo'] = []
        for pvideo in response.css('#dedepagetitles option'):
            feed['pvideo'].append(pvideo.css('::text').extract_first())
        if not feed['pvideo']:
            feed.pop('pvideo')
        if feed:
            yield feed