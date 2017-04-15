# -*- coding: utf-8 -*-

import json
import time
from datetime import datetime
import pymongo
import re
from amwatcher_spider.spiders.base import BaseSpider, KeywordEscape
from random import random
from scrapy import Spider, Request
from scrapy.http import HtmlResponse
from collections import defaultdict
import logging
import requests
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

PROXY_KEY = 'amwatcher:spider:login_proxy:%s'

class IqiyiSpider(BaseSpider):
    name = 'iqiyi'
    bangumi_pattern = 'http://so.iqiyi.com/so/q_%(keyword)s_ctg_动漫_t_0_page_1_p_1_qc_0_rd__site_iqiyi_m_1_bitrate_'
    drama_pattern = 'http://so.iqiyi.com/so/q_%(keyword)s_ctg_电视剧_t_0_page_1_p_1_qc_0_rd__site_iqiyi_m_1_bitrate_'
    variety_pattern = 'http://so.iqiyi.com/so/q_%(keyword)s_ctg_综艺_t_0_page_1_p_1_qc_0_rd__site_iqiyi_m_1_bitrate_'
    download_delay = 2
    handle_httpstatus_list = [302]
    use_proxy = False
    
    def __init__(self, mode='prod', *args, **kwargs):
        super(IqiyiSpider, self).__init__(mode)
    
    def start_requests(self):
        self.start_timestamp = datetime.now()
        
        for kobj in self.mongo_keywords.find({'status': 'activated', '$or': [{ 'tags': '爱奇艺'}, {'type': 'anime'}]}):
            search_words = [kobj['keyword']]
            if 'alias' in kobj:
                search_words.extend(kobj['alias'])
            for search_word in search_words:
                search_word_url = KeywordEscape(search_word)
                if kobj['type'] == 'anime': 
                    bangumi_url = self.bangumi_pattern % { 'keyword': search_word_url }
                    feed = {
                        'source': 'iqiyi',
                        'type': 'bangumi',
                        'search_word': search_word,
                        'keyword_id': kobj['_id'],
                        'keyword_title': kobj['keyword'],
                    }
                    yield Request(url=bangumi_url, meta={ 
                        'kobj': kobj, 
                        'feed': feed, 
                    }, callback=self.parse_bangumi)
                elif kobj['type'] == 'drama': 
                    drama_url = self.drama_pattern % { 'keyword': search_word_url }
                    feed = {
                        'source': 'iqiyi',
                        'type': 'drama',
                        'search_word': search_word,
                        'keyword_id': kobj['_id'],
                        'keyword_title': kobj['keyword'],
                    }
                    yield Request(url=drama_url, meta={ 
                        'kobj': kobj, 
                        'feed': feed, 
                    }, callback=self.parse_drama)
                else:
                    continue
                    logger.warning('发现不合法关键字')

    def parse_bangumi(self, response):
        ''' 爬取爱奇艺番剧
        
        @url http://so.iqiyi.com/so/q_暗芝居_ctg_动漫_t_0_page_1_p_1_qc_0_rd__site_iqiyi_m_1_bitrate_
        '''
        meta = response.meta
        kobj = meta['kobj']
        
        logger.info('开始爬取番剧, URL: %s' % response.url)
        feed = dict(meta['feed'])
        
        search_results = response.css('.list_item') 
        
        if not search_results:
            logger.info('[%s] 未找到番剧...' % kobj['keyword'])
        for series in search_results:
            link = series.css('.result_title a')
            if link.css('::attr(data-widget-block)').extract_first() == 'block':
                # 官方番剧，获取剧集
                feed['title'] = link.css('::attr(title)').extract_first()
                # if re.match('第.+季', feed['title'].split()[-1]):
                    # feed['title'] = feed['title'].split[:-1]
                    # feed['season'] = title.split[-1]
                # else:
                    # feed['season'] = 'NO_SEASON'
                feed['tags'] = series.css('.result_info_cont-half a::attr(title)').extract()
                feed['description'] = series.css('.result_info_txt::text').extract_first()
                for ep in series.css('ul[data-tvlist-elem="list"] .album_item'):
                    epfeed = dict(feed)
                    if ep.css('.icon-album-vip'):
                        epfeed['title'] += '(爱奇艺VIP)'
                    epfeed['title'] += ' %s' % ep.css('a::attr(title)').extract_first()
                    epfeed['href'] = ep.css('a::attr(href)').extract_first()
                    epfeed['scrapy_time'] = datetime.now()
                    epfeed['scrapy_start_time'] = self.start_timestamp
                    epfeed['upload_time'] = epfeed['scrapy_time']
                    epfeed['uploader'] = 'iqiyi'
                    exfeed = self.mongo_feeds.find_one({
                        'title': epfeed['title'],
                        'keyword_title': kobj['keyword'],
                    })
                    if exfeed:
                        logger.info('该条目已存在，略过...')
                    else:
                        yield epfeed
            else:
                continue # 非官方资源质量太差，仅收录官方。。
                '''
                epfeed = dict(feed)
                epfeed['type'] = 'upbangumi'
                epfeed['title'] = link.css('::attr(title)').extract_first()
                
                epfeed['href'] = link.css('::attr(href)').extract_first()
                epfeed['scrapy_time'] = datetime.now()
                epfeed['scrapy_start_time'] = self.start_timestamp
                try:
                    epfeed['upload_time'] = datetime.strptime(
                        series.css('em.result_info_desc::text').extract_first(), 
                        '%Y-%m-%d'
                    )
                except Exception:
                    epfeed['upload_time'] = epfeed['scrapy_time']
                # feed['season'] = 'NO_SEASON'
                # 检查是否存在
                exfeed = self.mongo_feeds.find_one({
                    'title': epfeed['title'],
                    'keyword_title': kobj['keyword'],
                })
                if exfeed:
                    logger.info('该条目已存在，略过...')
                else:
                    yield epfeed
                '''

    def parse_drama(self, response):
        ''' 爬取爱奇艺电视剧
        
        @url http://so.iqiyi.com/so/q_暗芝居_ctg_动漫_t_0_page_1_p_1_qc_0_rd__site_iqiyi_m_1_bitrate_
        '''
        meta = response.meta
        kobj = meta['kobj']
        
        logger.info('开始爬取电视剧, URL: %s' % response.url)
        feed = dict(meta['feed'])
        
        search_results = response.css('.list_item') 
        
        if not search_results:
            logger.info('[%s] 未找到电视剧...' % kobj['keyword'])
        for series in search_results:
            link = series.css('.result_title a')
            if link.css('::attr(data-widget-block)').extract_first() == 'block':
                # 官方番剧，获取剧集
                feed['title'] = link.css('::attr(title)').extract_first()
                feed['tags'] = series.css('.result_info_cont-half a::attr(title)').extract()
                feed['description'] = series.css('.result_info_txt::text').extract_first()
                for ep in series.css('ul[data-tvlist-elem="list"] .album_item'):
                    epfeed = dict(feed)
                    if ep.css('.icon-album-vip'):
                        epfeed['title'] += '(爱奇艺VIP)'
                    if ep.css('.icon-yugao-new'):
                        continue # 跳过预告
                    epfeed['title'] += ' %s' % ep.css('a::attr(title)').extract_first()
                    epfeed['href'] = ep.css('a::attr(href)').extract_first()
                    epfeed['scrapy_time'] = datetime.now()
                    epfeed['scrapy_start_time'] = self.start_timestamp
                    epfeed['upload_time'] = epfeed['scrapy_time']
                    epfeed['uploader'] = 'iqiyi'
                    exfeed = self.mongo_feeds.find_one({
                        'title': epfeed['title'],
                        'keyword_title': kobj['keyword'],
                        'source': epfeed['source'],
                    })
                    if exfeed:
                        logger.info('该条目已存在，略过...')
                    else:
                        yield epfeed
            else:
                continue # 非官方资源质量太差，仅收录官方。。
                '''
                epfeed = dict(feed)
                epfeed['type'] = 'updrama'
                epfeed['title'] = link.css('::attr(title)').extract_first()
                epfeed['upload_time'] = datetime.strptime(
                    series.css('em.result_info_desc::text').extract_first(), 
                    '%Y-%m-%d'
                )
                epfeed['href'] = link.css('::attr(href)').extract_first()
                epfeed['scrapy_time'] = datetime.now()
                epfeed['scrapy_start_time'] = self.start_timestamp
                # feed['season'] = 'NO_SEASON'
                # 检查是否存在
                exfeed = self.mongo_feeds.find_one({
                    'title': epfeed['title'],
                    'keyword_title': kobj['keyword'],
                })
                if exfeed:
                    logger.info('该条目已存在，略过...')
                else:
                    yield epfeed
                '''