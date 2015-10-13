[General]
# 3d bucket
bucketName: ${bucketname}
# user specific
profileName: ${profilename}
# terrain files base path
bucketpath: 1.0.0/ch.swisstopo.terrain.3d/default/20151231/4326/
# chunks per process (that's a maximum)
maxChunks: 50
# when using aws sqs queue, the name of the queue
sqsqueue: terrain_20150924
# proc factor (total processes = factor * num_cpus_on_machine
procfactor: 2

[Extent]
# below is region around thun
minLon: 7.49432
maxLon: 7.69554
minLat: 46.68688
maxLat: 46.83431
# below is whole switzerland
#minLon: 5.86725126512748
#maxLon: 10.9209100671547
#minLat: 45.8026860136571
#maxLat: 47.8661652478939
# fullonly: 0 -> inludes all tiles that intersect, even partly, with extent
# fullonly: 1 -> include only tiles that fully intersect with extent
fullonly: 0

[Extensions]
# watermask: 0 -> no watermask
# watermask: 1 -> include watermask (use table public.lakes per default)
watermask: 0
# lighting: 0 -> no light
# lighting: 1 -> include unit vectors
lighting: 0

[Zooms]
tileMinZ: 8
tileMaxZ: 17

[8]
# Should be replaced with dhm25_256
tablename: dhm25_128m

[9]
tablename: dhm25_128m

[10]
tablename: dhm25_64m

[11]
tablename: bl_128m

[12]
tablename: bl_64m

[13]
tablename: bl_32m

[14]
tablename: bl_8m

[15]
tablename: bl_2m

[16]
tablename: bl_1m

[17]
tablename: bl_0_5m

[18]
tablename: bl_0_5m
