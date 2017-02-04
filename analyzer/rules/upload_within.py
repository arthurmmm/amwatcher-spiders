# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
    
def tweak(kobj, feed, month=1):
    # cast in tag
    upload_time = feed['upload_time']
    if 'tags' not in kobj:
        return True, feed
    match_num = 0
    for ktag in kobj['tags']:
        for ftag in feed['tags']:
            if ktag in ftag:
                match_num += 1
        if ktag in feed['title']:
            match_num += 1
        if ktag in feed['description']:
            match_num += 1
    if match_num >= 1:
        return True, feed
    else:
        return False, feed