#!/usr/bin/env python
#-*- coding: utf-8 -*-

'''
Simple test of datum shift without and with grid

'''


import os
import pyproj


DEBUG = True

_here = os.path.dirname(os.path.abspath(__file__))
proj_datadir = os.path.join(_here, '../proj_data')


os.environ["PROJ_LIB"] = proj_datadir

if DEBUG:
    os.environ["PROJ_DEBUG"] = '5'


LV03_y, LV03_x = 806260.46, 128261.51
WGS84_x, WGS84_y = 8.84215, 45.91317

CH_1903_LV03 = pyproj.Proj(init="CH:1903_LV03")
EPSG_21781 = pyproj.Proj(init="EPSG:21781")
EPSG_4326 = pyproj.Proj(init="EPSG:4326")


print "LV03 --> WGS1984"
print "LV03           = (%0.6f, %0.6f)" % (pyproj.transform(EPSG_21781, EPSG_4326, LV03_y, LV03_x))
print "LV03 NTv2 grid = (%0.6f, %0.6f)" % (pyproj.transform(CH_1903_LV03, EPSG_4326, LV03_y, LV03_x))
print "WGS194 NAVREF  = (%0.6f, %0.6f)" % (10.114914476, 46.274111523)

'''
>>> LV03 --> WGS1984
>>> LV03  = (10.114893, 46.274112)
>>> LV03 (grid) = (10.114914, 46.274111)
>>> WGS194 NAVREF =  (10.114914, 46.274112)
'''
