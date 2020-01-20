# 3d-forge, take off

This document is written from toby for toby, or for the next operator that will start
the AMI (vpc-tileforge3d-20180329) to get the beast ready to rock.

## Database

### Adaption to make the database accessible from outside

```bash
$ vi /var/lib/postgresql/9.4/main/pg_hba.conf
host    all             all              0.0.0.0/0                       md5
host    all             all              ::/0                            md5

$ vi /var/lib/postgresql/9.4/main/postgresql.conf
listen_addresses = '*'
```

### Start database pointing to the right settings

```bash
$ /usr/lib/postgresql/9.4/bin/pg_ctl -D /var/lib/postgresql/9.4/main/ start
```

### For paranoid people, making sure that only the databases on the tileforge instance are accessible

```bash
$ iptables -A OUTPUT -p tcp --dport 5432 -d localhost -j ACCEPT
$ iptables -A OUTPUT -p tcp --dport 5432 -j DROP


# to drop rules
sudo iptables -L --line-numbers
sudo iptables -D OUTPUT 2
```

## Configuration

### Git

```bash
$ vi .ssh/config
Host *
  ForwardAgent yes
```

```bash
$ git config --global user.name "xxxx xxxx" 
$ git config --global user.email "tobias.reber@swisstopo.ch" 
```

### Reframe

Don't know why, but the tool uses Reframe.exe for the transformation of the
coordinates. Anyhow, this tool uses a valid licence file (that is valid
for just a year). The licence file (provided by the cadastral survey
- ask Michael Burkhard). The one for 2020 is stored in the keepass database
of IGEB-B under tileforge.

```bash
/root/Console/x64/geosuite.lic
```

### 3d Forge config

**Do not forget /root/.bashrc**
```bash
$ vi .bashrc
export PGUSER=pgkogis
export PGPASS=pgkogis_borudel
export DBHOST=localhost
export BUCKETNAME=3dtiles-dev
export PROFILENAME= # TODO better
export LOGFILEFOLDER=/var/log/3d-forge
```

AWS services (credentials) have meanwhile been configuret to the maschine and not to a profile:
```bash
$ mv .aws aws_config
```

Most important is the adaption of the following files easiest by checking out
```bash
$ git fetch
$ git checkout -b ltrea_testing_terrain origin/ltrea_testing_terrain
$ vi config/terrain/database.cfg
$ vi config/terrain/tms.cfg
```

## TAKE OFF

```bash
$ make createdb

$ make setupfunctions

$ make populate
# populates the database
# check with psql:
# check with qgis (here how to use ssh tunnel trough bit-proxy, if neccessary from swisstopo desktop: ssh -L 5555:localhost:5432 root@the_beast)

$ make tmspyramid
# writes the terrain tiles directly to S3

$ make tmsmetadata
# safes the generated layer.js index file in 3d-forge/.tmp
# to make changes, edit forge/lib/tiler.py (https://github.com/geoadmin/3d-forge/blob/ltrea_testing_terrain/forge/lib/tiler.py#L456)
# as there is a layer.js
# and a vip layer_cf on prod (see here: aws s3 ls s3://ioazqwe8i7q2zof-tms3d/1.0.0/ch.swisstopo.terrain.3d/default/20180601/4326/)

```

## Nice to know

### Testing if database is listening

```bash
# on the machine
netstat -tulpn | grep LIST

# outside
nc -v -z xxx.xxx.xxx.xxx 5432
```

### Some SQS

```bash
# the setup is that only terrain_* queues can be created
$ aws sqs create-queue --queue-name=terrain_har --region=eu-west-1
$ aws sqs delete-queue --queue-url=https://eu-west-1.queue.amazonaws.com/443130343732/terrain_har --region=eu-west-1

# https://docs.aws.amazon.com/cli/latest/reference/sqs/
```
