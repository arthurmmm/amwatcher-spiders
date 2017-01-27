# -*- coding: utf-8 -*-

import re

def tweak(kobj, feed):
    if matchKeyword(kobj['keyword'], feed):
        feed['match_keyword'] = kobj['keyword']
        return True, feed
    if 'alias' in kobj:
        for kw in kobj['alias']:
            if matchKeyword(kw, feed):
                feed['match_keyword'] = kw
                return True, feed
    return False, feed
    
def matchKeyword(kw, feed):
    words = [ w for w in kw.split() ]
    word_pattern = '.*'.join(words)
    # TODO - wildly match chinese episode name
    if not re.search(word_pattern, feed['title'], re.I):
        return False
    else:
        return True