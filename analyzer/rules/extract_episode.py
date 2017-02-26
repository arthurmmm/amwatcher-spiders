# -*- coding: utf-8 -*-

import re
import logging

logger = logging.getLogger('__main__')

CHN_INT = '[一二三四五六七八九十]'
CHN_MAP = {
    '一': '1',
    '二': '2',
    '三': '3',
    '四': '4',
    '五': '5',
    '六': '6',
    '七': '7',
    '八': '8',
    '九': '9',
    '十': '10',
}

def toInt(str):
    try:
        return int(str)
    except ValueError:
        if str == '剧场版':
            return 0
    

def tweak(feed, condition, *args):
    # 去除月份、年份等常见干扰项
    regex_exclude = [
        re.compile('(\d+)[月|年|春|夏|秋|冬|金|木|水|火|土]', re.I), 
        re.compile('(\d+)p', re.I),  # 720p, 1080p ....
        re.compile('(\d+)时', re.I),  
        re.compile('(\d+)時', re.I),  
        re.compile('pv\s*(\d+)', re.I),  
        re.compile('特典\s*(\d+)', re.I),  
        re.compile('特报\s*(\d+)', re.I),  
        re.compile('预告\s*(\d+)', re.I), 
        re.compile('part\s*(\d+)', re.I), 
        re.compile('剧场版\s*(\d+)'),
        re.compile('OVA\s*(\d+)'),
    ]
    # 强匹配季数
    regex_season = [
        re.compile('season[\s\.]?(\d+)', re.I), # season 01
        re.compile('SE[\s\.]?(\d+)', re.I), # SE01
        re.compile('s[\s\.]?(\d+)', re.I), # S01
        re.compile('(\d+)\s?季'), # 1季
        re.compile('(%s)\s?季' % CHN_INT), # 一季
    ]
    # 强匹配集数
    regex_strong = [
        re.compile('(?<![a-zA-Z])episode[\s\.]?(\d+)', re.I), # episode 01
        re.compile('(?<![a-zA-Z])ep[\s\.]?(\d+)', re.I), # ep01
        re.compile('(?<![a-zA-Z])E[\s\.]?(\d+)', re.I), # E01
        re.compile('(?<![a-zA-Z])sp[\s\.](\d+)\s?', re.I), # sp01
        re.compile('(\d+)\s?话'), # X话
        re.compile('(\d+)\s?回'), # X回
        re.compile('(\d+)\s?集'), # X集
        
        # TODO - 处理中文集数
        # re.compile('(?P<ep>%s+)\s*话' % CHN_INT), # X话
        # re.compile('(?P<ep>%s+)\s*回' % CHN_INT), # X回
        # re.compile('(?P<ep>%s+)\s*集' % CHN_INT), # X集
    ]
    # 日期匹配
    regex_date = [
        re.compile('(?<![0-9])\d{2}(\d{6})(?![0-9])'), # 20170203
        re.compile('(?<![0-9])(\d{6})(?![0-9])'), # 170203
        re.compile('(?<![0-9])(\d{2}\.\d{2}.\d{2})(?![0-9])'), # 17.02.03
        re.compile('(?<![0-9])\d{2}(\d{2}\.\d{2}.\d{2})(?![0-9])'), # 2017.02.03
    ]
    # 弱匹配
    regex_weak = [
        re.compile('(?<![0-9])0(\d)(?=[^\w]|$)'), # 优先匹配0开头的数字 01 02 ...
        re.compile('(?<![0-9])(\d\d\d)(?=[^\w]|$)'), # 匹配三位数
        re.compile('(?<![0-9])(\d\d)(?=[^\w]|$)'), # 匹配两位数
        re.compile('(?<![0-9])(\d)(?=[^\w]|$)'), # 匹配一位数
    ]
    
    match_title = str(feed['title'])
    feed['date_episode'] = []
    feed['episode'] = []
    feed['season'] = []
    
    # 去除常见干扰项
    for regex in regex_exclude:
        match_title = regex.sub('', match_title)
    # 去除特定干扰项
    logger.debug(condition)
    if 'exclude_in_episode' in condition:
        logger.debug(match_title)
        for excule_pattern in condition['exclude_in_episode']:
            # regex = re.compile(excule_pattern)
            match_title = re.sub(excule_pattern, '', match_title, flags=re.I)
        logger.debug(match_title)
    
    # 强匹配季数
    for regex in regex_season:
        while True:
            ep_match = regex.search(match_title)
            if not ep_match:
                break
            # 匹配后从match_title中删去对应字符
            season_text = ep_match.group(1)
            # logger.debug(season_text)
            if season_text in CHN_MAP:
                season = CHN_MAP[season_text]
            else:
                season = season_text
            feed['season'].append(season)
            match_title = regex.sub('', match_title, count=1)
    
    # 强匹配集数
    for regex in regex_strong:
        while True:
            ep_match = regex.search(match_title)
            if not ep_match:
                break
            
            feed['episode'].append(ep_match.group(1))
            match_title = regex.sub('', match_title, count=1)

    # 日期匹配
    for regex in regex_date:
        while True:
            ep_match = regex.search(match_title)
            if not ep_match:
                break
            # 匹配后从match_title中删去对应字符
            feed['date_episode'].append(ep_match.group(1).replace('.', ''))
            match_title = regex.sub('', match_title, count=1)
    
    logger.debug(match_title)
    # 删去片名以及片名前的字符
    kw_pattern = '.*?'.join(feed['search_word'].split())    
    match_title = re.sub('^.*?'+kw_pattern, '', match_title, count=1, flags=re.I)
    logger.debug(match_title)
    
    # 弱匹配（如果已经有date_episode或者episode则跳过此步骤）
    if feed['date_episode'] or feed['episode']:
        pass
    else:
        for regex in regex_weak:
            while True:
                ep_match = regex.search(match_title)
                if not ep_match:
                    break
                # 匹配后从match_title中删去对应字符
                feed['episode'].append(ep_match.group(1))
                match_title = regex.sub('', match_title, count=1)
    
    if not feed['date_episode']:
        feed.pop('date_episode')
    else:
        feed['date_episode'].sort()
    if not feed['episode']:
        feed.pop('episode')
    else:
        feed['episode'].sort()
    if not feed['season']:
        feed['season'] = ['-1']
    else:
        feed['season'].sort()

    if 'date_episode' not in feed and 'episode' not in feed:
        return False, feed
    else:
        return True, feed
    