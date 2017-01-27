# -*- coding: utf-8 -*-

import re
    
def tweak(kobj, feed):
    # cast in tag
    if 'casts' not in kobj:
        return True, feed
    match_num = 0
    for cast in kobj['casts']:
        for tag in feed['tags']:
            if cast in tag:
                match_num += 1
        if cast in feed['title']:
            match_num += 1
        if cast in feed['description']:
            match_num += 1
    if match_num >= 1:
        return True, feed
    else:
        return False, feed