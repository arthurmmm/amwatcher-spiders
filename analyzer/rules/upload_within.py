# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
    
def tweak(feed, condition, days=365):
    # cast in tag
    upload_time = feed['upload_time']
    if (datetime.now() - upload_time) > timedelta(days=365):
        return False, feed
    else:
        return True, feed