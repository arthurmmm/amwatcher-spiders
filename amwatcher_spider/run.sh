#!/bin/sh

nohup scrapy crawl bilibili > /var/tmp/bilibili.out 2>&1 &