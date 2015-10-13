# 3d-forge
Read/Write quantized-mesh tiles

To clone use the --recursive option to get all submodules.
`git clone --recursive https://github.com/geoadmin/3d-forge`

## Set up the required variables in your .bashrc

    export PGSPASS=xxx

    export DBTARGET=xxx

    export BUCKETNAME=xxx

    export PROFILENAME=xxx

    export LOGFILEFOLDER=xxx

## Getting started

    make all

## Create the database and import the shapefiles in the DB

    make createdb populate

## Test a tile generated in S3

    wget --header="Accept-Encoding: gzip,deflate" http://3d.geo.admin.ch/1.0.0/ch.swisstopo.terrain.3d_water/default/20151231/4326/12/4268/3110.terrain -O 12_43268_3110.terrain.gz
    gzip -d 12_43268_3110.terrain.gz

## Interactive programming

    source venv/bin/activate
    ipython
    run {yourScript}.py

#### Enter debug mode

    %debug

#### Get the latest traceback

    %tb


## Styling

#### Check styling

    make lint

#### Fix styling (only pep8 errors)

    make autolint

### Copy a file to S3 from command line

    aws --profile tms3d_filestorage s3 cp layer.json  s3://tms3d.geo.admin.ch/xxx/layer.json

## Create 3d-tiling instance

- Create instance here: https://tilegenmanager.prod.bgdi.ch/index/index

- Connect to created instance with user `tileforge`

- Adapt your configurations (.bashrc, .vim, .screenrc) if desired

- connect to db host

- sudo su postgres

  * change password of superuser to xxx with the following sql query:
    ```sql
    ALTER role pgkogis WITH PASSWORD 'xxxxxx';
    ```

  * exit sudo

- add credentials to .boto file

- add configuration to .aws/config

- add credentials to .aws/credentials

- mount zadara with `sudo -u root /bin/mount /var/local/cartoweb`

- get project with `git clone --recursive https://github.com/geoadmin/3d-forge`

- install with `make install`

- create db with `make createdb`, adapt `database.cfg` for different data sets

- create tiles with `tmspyramid`, adapt `tms.cfg` for different tiler
  configurations

- you can also deactivate stats collection by setting `track_activities` to off in `/etc/postgresql/9.1/main/postgresql.conf`

- choose the appropriate logging level for postgres client_min_messages = error and log_min_messages = error and log_min_error_statement = error

- if you don't have tileforge user make sure you're using md5 mode in pg_hba.conf (local  all  all  md5)

## Remove logs

    rm -f /var/log/tileforge/*.log

    sudo su postgres

    rm -r /var/log/postgresql/*

## SQL Helper Functions
During the installation some sql functions are installed on the target database.
### meta.sql
This script is creating a view called public.meta to the database. This view contains useful information (table size, index size, row count) for the monitoring of database growth during import. note: the rowcount is coming from the statistics collector and is only containing values during import. 

```sql
$ psql -d forge -c "SELECT * FROM meta;"
         Table         | Size Total | External Size | rowcount
-----------------------+------------+---------------+----------
 break_lines_0_25m     | 94 GB      | 27 GB         |        0
 break_lines_0_5m      | 38 GB      | 11 GB         |        0
 break_lines_1m        | 19 GB      | 5631 MB       |        0
 break_lines_2m        | 10078 MB   | 2968 MB       |        0
 break_lines_4m        | 1967 MB    | 575 MB        |        0
 break_lines_8m        | 904 MB     | 265 MB        |        0
 break_lines_16m       | 653 MB     | 194 MB        |        0
 break_lines_32m       | 458 MB     | 136 MB        |        0
 mnt25_simplified_100m | 390 MB     | 113 MB        |        0
 break_lines_64m       | 330 MB     | 96 MB         |        0
 spatial_ref_sys       | 3360 kB    | 176 kB        |        0
 topology              | 24 kB      | 24 kB         |        0
 layer                 | 24 kB      | 24 kB         |        0
 zoomlevel_6           | 16 kB      | 8192 bytes    |        1
 zoomlevel_4           | 16 kB      | 8192 bytes    |        1
 zoomlevel_3           | 16 kB      | 8192 bytes    |        1
 zoomlevel_8           | 16 kB      | 8192 bytes    |        1
 zoomlevel_2           | 16 kB      | 8192 bytes    |        1
 zoomlevel_7           | 16 kB      | 8192 bytes    |        1
 zoomlevel_5           | 16 kB      | 8192 bytes    |        1
 zoomlevel_0           | 16 kB      | 8192 bytes    |        1
 table_z17_extent      | 16 kB      | 8192 bytes    |        0
 zoomlevel_1           | 16 kB      | 8192 bytes    |        1
```

### visualize_tms_grid.sql
This script is installing the following sql functions to the database:
* public.bgdi_global_geodetic_recursive(geom geometry,maxlevels integer)
* public.bgdi_lonlat2tile(lon double precision DEFAULT 7.0, lat double precision DEFAULT 46.0, zoom integer DEFAULT 5)

**bgdi_global_geodetic_recursive(geom geometry,maxlevels integer)** can be used to visualize tile geometries and label them with their tms address or google address. You have to pass an input geometry and the maximal depth / zoomlevel to the function. Of course these parameters should be set with caution. Generating all the tiles for a big geometry until zoomlevel 20 will take hours!

```sql
$ psql -c "select id,zoomlevel,x,y,st_astext(the_geom),label_tsm,label_google FROM bgdi_global_geodetic_recursive(st_setsrid('BOX(8.15974 46.75665,8.16465 46.75913)'::box2d::geometry, 4326),5);" -d forge
 id | zoomlevel | x  | y  |                            st_astext                            | label_tsm | label_google
----+-----------+----+----+-----------------------------------------------------------------+-----------+--------------
  0 |         0 |  1 |  0 | POLYGON((0 -90,0 90,180 90,180 -90,0 -90))                      | 0/1/0     | 0/1/0
  1 |         1 |  2 |  0 | POLYGON((0 0,0 90,90 90,90 0,0 0))                              | 1/2/0     | 1/2/1
  2 |         2 |  4 |  0 | POLYGON((0 45,0 90,45 90,45 45,0 45))                           | 2/4/0     | 2/4/3
  3 |         3 |  8 |  2 | POLYGON((0 45,0 67.5,22.5 67.5,22.5 45,0 45))                   | 3/8/1     | 3/8/6
  4 |         4 | 16 |  5 | POLYGON((0 45,0 56.25,11.25 56.25,11.25 45,0 45))               | 4/16/3    | 4/16/12
  5 |         5 | 32 | 11 | POLYGON((5.625 45,5.625 50.625,11.25 50.625,11.25 45,5.625 45)) | 5/33/7    | 5/33/24

```

This function can be used for the visualization in qgis:
![image](https://cloud.githubusercontent.com/assets/5286659/9004616/c08be376-3777-11e5-945b-2ce950f2ec12.png)

The function **public.bgdi_lonlat2tile(lon double precision DEFAULT 7.0, lat double precision DEFAULT 46.0, zoom integer DEFAULT 5)** can be used to calculate the tile address at a given zoomlevel. The function returns a point geomtry:
* x-coordinate -> X Tile Address
* y-coordinate -> Y Tile Address a la google
* z-coordinate -> Y Tile Address global geodetic (TSM)
```sql
$ psql -c "select st_astext(bgdi_lonlat2tile(8.159259,46.758162,17));" -d forge
          st_astext
------------------------------
 POINT Z (137013 99584 31487)
(1 Zeile)
```

### watermask.sql
This script is installing the following sql functions to the database:
* bgdi_watermask_rasterize(geometry, integer, integer, regclass, text)

**bgdi_watermask_rasterize(geometry, integer, integer, regclass, text)** can be used to create the watermask for a given tile geometry. All the lake intersections within this tile will be rasterized, the raster dimension (pixel width and height) and the lake geometry table has to be set within the function call.

The input parameters of the function are:
```sql
bgdi_watermask_rasterize(
bbox geometry                 -- geometry object with the tile geometry
, width integer               -- tile width in pixels
, height integer              -- tile height in pixels
, watermask_table regclass    -- schema.table containing lake geometry
, watermask_geom_column text  -- geometry column
)
```
The returned raster is of type ``'1BB' 1-bit boolean`` [1]:
```
1 -> water
0 -> land
```
Example Query:
```SQL
SELECT bgdi_watermask_rasterize(st_setsrid('POLYGON((6.865 46.379, 6.865 46.383 , 6.869 46.383 , 6.869 46.379, 6.865 46.379 ))'::geometry,4326), 256,256,'v25_pri25_a_seeflaechen'::regclass,'the_geom'::text)as geom;
```

The current implementation is rasterizing the vector features with the GDAL ALL_TOUCHED=TRUE option.
![image](https://cloud.githubusercontent.com/assets/5286659/9340301/36695576-45ef-11e5-91a1-881c6819a03e.png)

[1] http://postgis.net/docs/RT_ST_BandPixelType.html
