#!/bin/sh
# -*- coding: utf-8 -*-
path=$1
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
workon amwatcher-spider
cd $path
scrapy crawl bilibili 