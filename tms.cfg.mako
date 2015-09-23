[General]
# 3d bucket
bucketName: ${bucketname}
# user specific
profileName: ${profilename}
# terrain files base path
bucketpath: 1.0.0/ch.swisstopo.terrain.3d/default/20151231/4326/
# chunks per process (that's a maximum)
maxChunks: 50

[Extent]
minLon: 5.86725126512748
maxLon: 10.9209100671547
minLat: 45.8026860136571
maxLat: 47.8661652478939
# fullonly: 0 -> inludes all tiles that intersect, even partly, with extent
# fullonly: 1 -> include only tiles that fully intersect with extent
fullonly: 0

[Zooms]
tileMinZ: 8
tileMaxZ: 17

[8]
tablename: dhm25_64m

[9]
tablename: bl_128m

[10]
tablename: bl_64m

[11]
tablename: bl_32m

[12]
tablename: bl_16m

[13]
tablename: bl_8m

[14]
tablename: bl_4m

[15]
tablename: bl_2m

[16]
tablename: bl_1m

[17]
tablename: bl_0_5m
