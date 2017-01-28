# -*- coding: utf-8 -*-

import re

CHN_INT = '[一二三四五六七八九十]'

def toInt(str):
    try:
        return int(str)
    except ValueError:
        if str == '剧场版':
            return 0
    

def tweak(kobj, feed):
    # 集数格式库
    regex_strong = [
        re.compile('episode[\s\.]?(\d+)', re.I), # episode 01
        re.compile('ep[\s\.]?(\d+)', re.I), # ep01
        re.compile('E[\s\.]?(\d+)', re.I), # E01
        re.compile('sp[\s\.](\d+)\s?', re.I), # sp01
        re.compile('(\d+)\s?话'), # X话
        re.compile('(\d+)\s?回'), # X回
        re.compile('(\d+)\s?集'), # X集
        re.compile('(剧场版)'),
        # TODO - 处理中文集数
        # re.compile('(?P<ep>%s+)\s*话' % CHN_INT), # X话
        # re.compile('(?P<ep>%s+)\s*回' % CHN_INT), # X回
        # re.compile('(?P<ep>%s+)\s*集' % CHN_INT), # X集
    ]
    regex_weak = [
        re.compile('0(\d)'), # 优先匹配0开头的数字 01 02 ...
        re.compile('\s(\d\d)\s'), # 匹配两位数周围带空格的
        re.compile('\s(\d\d)'), # 匹配两位数周围带空格的
        re.compile('(\d\d)\s'), # 匹配两位数周围带空格的
        re.compile('\s(\d+)\s'), # 匹配数字周围带空格的
        re.compile('\s(\d+)'), # 匹配数字周围带空格的
        re.compile('(\d+)\s'), # 匹配数字周围带空格的
        re.compile('(\d\d)'), # 匹配两位数
        re.compile('(\d)'), # 匹配一位数
        re.compile('(\d+)'), # 匹配所有数字
    ]
    # 匹配标题
    for regex in regex_strong:
        ep_match = [ e for e in regex.finditer(feed['title']) ]
        if ep_match:
            print([ e.group(0) for e in ep_match ])
            episode = toInt(ep_match[-1].group(1)) # 多个匹配优先匹配靠后的
            feed['episode'] = episode
            return True, feed
    # 匹配片名后的字段
    kw_pattern = '.*?'.join(feed['match_keyword'].split())
    kw_pattern = '.*%s(.*)' % kw_pattern
    regex = re.search(feed['title'], kw_pattern)
    if regex:
        after_kw = regex.group(1)
    else:
        after_kw = feed['title']
        
    for regex in regex_weak:
        ep_match = [ e for e in regex.finditer(after_kw) ]
        if ep_match:
            print([ e.group(0) for e in ep_match ])
            episode = toInt(ep_match[-1].group(1)) # 多个匹配优先匹配靠后的
            feed['episode'] = episode
            return True, feed
    else:
        # 未找到集数，丢弃该条目
        return False, feed
    