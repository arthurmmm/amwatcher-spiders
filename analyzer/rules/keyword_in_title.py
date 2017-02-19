# -*- coding: utf-8 -*-

import re

def tweak(feed, condition, *args):
    try:
        if matchKeyword(condition['keyword'], feed):
            feed['match_keyword'] = condition['keyword']
            return True, feed
        if 'alias' in condition:
            for kw in condition['alias']:
                if matchKeyword(kw, feed):
                    feed['match_keyword'] = kw
                    return True, feed
    except Exception as e:
        print(feed)
        print(condition)
        raise
    return False, feed
    
def matchKeyword(kw, feed):
    words = [ w for w in kw.split() ]
    word_pattern = '.*'.join(words)
    word_pattern = '(?<!\w)%s(?!\w)' % word_pattern
    # TODO - wildly match chinese episode name
    if not re.search(word_pattern, feed['title'], re.I):
        return False
    else:
        return True