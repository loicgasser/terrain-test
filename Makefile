VENV = venv
PYTHON_CMD = $(VENV)/bin/python
FLAKE8_CMD = $(VENV)/bin/flake8
AUTOPEP8_CMD = $(VENV)/bin/autopep8
PIP_CMD := $(VENV)/bin/pip
MAKO_CMD = $(VENV)/bin/mako-render
PREFIX ?= 1/
PYTHON_FILES := $(shell find scripts/* forge/* -name '*.py')
USERNAME := $(shell whoami)
TILEJSON_TEMPLATE ?= configs/raster/ch_swisstopo_swisstlm3d-wanderwege.cfg

MAX_LINE_LENGTH=90
PEP8_IGNORE="E128,E221,E241,E251,E272,E711,E731,W503"

# E128: continuation line under-indented for visual indent
# E221: multiple spaces before operator
# E241: multiple spaces after ':'
# E251: multiple spaces around keyword/parameter equals
# E272: multiple spaces before keyword
# E711: comparison to None should be 'if cond is None:' (SQLAlchemy's filter syntax requires this ignore!)
# E731: do not assign a lambda expression, use a def
# W503: line break before binary operator

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@echo
	@echo "- install            Install the app"
	@echo "- lint               Linter for python code"
	@echo "- test               Launch the tests"
	@echo "- all                All of the above"
	@echo "- autolint           Auto lint code styling"
	@echo "- console            Interactive psql console"
	@echo "- create             Create the database and user"
	@echo "- createuser         Create the user only"
	@echo "- createdb           Create the database only"
	@echo "- setupfunctions     Adds custom sql functions to the database"
	@echo "- populate           Populate the database with the TINs (shps)"
	@echo "- populatelakes      Populate the database with the lakes (polygons in WGS84)"
	@echo "- dropdb             Drop the database only"
	@echo "- dropuser           Drop the user only"
	@echo "- destroy            Drop the databasen and user"
	@echo "- counttiles         Count tiles in S3 bucket using a prexfix (usage: make counttiles PREFIX=12/)"
	@echo "- deletetiles        Delete tiles in S3 bucket using a prefix (usage: make deletetiles PREFIX=12/)"
	@echo "- listtiles          List tiles in S3 bucket using a prefix (usage: make listtiles PREFIX=12/)"
	@echo "- tmspyramid         Create the TMS pyramid based on the config file configs/terrain/tms.cfg"
	@echo "- tmsmetadata        Create the layers.json file (stored under 3d-forge/.tmp/layers.js)"
	@echo "- tmsstats           Provide statistics about the TMS pyramid"
	@echo "- tmsstatsnodb       Provide statistics about the TMS pyramid, without db stats"
	@echo "- tmscreatequeue     Creates AWS SQS queue with given settings (all tiles)"
	@echo "- tmsdeletequeue     Deletes current AWS SQS queue (you loose everything)"
	@echo "- tmsqueuestats      Get stats of AWS SQS queue"
	@echo "- tmscreatetiles     Creates tiles using the AWS SQS queue"
	@echo "- tilejson           Creates a tilejson provided a given template (usage: make tilejson TILEJSON_TEMPLATE=..."
	@echo "- clean              Clean all generated files"
	@echo "- cleanall           Clean all generated files and build tools"
	@echo
	@echo "Variables:"
	@echo
	@echo "- USERNAME (current value: $(USERNAME))"
	@echo "- PYTHON_CMD (current value: $(PYTHON_CMD))"
	@echo "- FLAKE8_CMD (current value: $(FLAKE8_CMD))"
	@echo "- AUTOPEP8_CMD (current value: $(AUTOPEP8_CMD))"
	@echo


.PHONY: all
all: install configs/terrain/database.cfg configs/terrain/tms.cfg configs/raster/database.cfg logging.cfg test lint

.PHONY: install
install:
	( if [ -d "$(VENV)" ] ; then echo 'Skipping venv creation'; else virtualenv $(VENV) --system-site-packages && ${PIP_CMD} install Cython --index-url https://pypi.fcio.net/simple/; fi ); \
	${PIP_CMD} install --index-url https://pypi.fcio.net/simple/ -e .;

configs/terrain/database.cfg:: configs/terrain/database.cfg.mako
	$(MAKO_CMD) --var "pgpass=$(PGPASS)" --var "dbhost=$(DBHOST)" --var "username=$(USERNAME)" $< > $@

configs/terrain/tms.cfg:: configs/terrain/tms.cfg.mako
	$(MAKO_CMD) --var "bucketname=$(BUCKETNAME)" --var "profilename=$(PROFILENAME)" $< > $@

configs/raster/database.cfg:: configs/raster/database.cfg.mako
	$(MAKO_CMD) --var "dbhost=$(DBTARGETLAYER)" --var "username=$(PGUSERLAYER)" --var "pgpass=$(PGPASSLAYER)" $< > $@

logging.cfg: logging.cfg.mako
	$(MAKO_CMD) --var "logfilefolder=$(LOGFILEFOLDER)" $< > $@

.PHONY: test
test:
	$(VENV)/bin/nosetests tests/

.PHONY: lint
lint:
	$(FLAKE8_CMD) --max-line-length=${MAX_LINE_LENGTH} --ignore=${PEP8_IGNORE} forge/

.PHONY: autolint
autolint:
	@echo $(PYTHON_FILES)
	$(AUTOPEP8_CMD) -v -i -a --max-line-length=${MAX_LINE_LENGTH} --ignore=${PEP8_IGNORE} $(PYTHON_FILES)

.PHONY: console
console:
	$(PYTHON_CMD) scripts/db_management.py console

.PHONY: create
create: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py create

.PHONY: createuser
createuser: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py createuser

.PHONY: createdb
createdb: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py createdb

.PHONY: setupfunctions
setupfunctions: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py setupfunctions

.PHONY: populate
populate: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py populate

.PHONY: populatelakes
populatelakes: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py populatelakes

.PHONY: dropuser
dropuser: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py dropuser

.PHONY: dropuser
dropdb: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py dropdb

.PHONY: destroy
destroy: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/db_management.py destroy

.PHONY: counttiles
counttiles:
	$(PYTHON_CMD) scripts/s3_tiles.py -p $(PREFIX) count

.PHONY: deletetiles
deletetiles:
	$(PYTHON_CMD) scripts/s3_tiles.py -p $(PREFIX) delete

.PHONY: listtiles
listtiles:
	$(PYTHON_CMD) scripts/s3_tiles.py -p $(PREFIX) list

.PHONY: tmspyramid
tmspyramid: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py create

.PHONY: tmsmetadata
tmsmetadata: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py metadata

.PHONY: tmsstats
tmsstats: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py stats

.PHONY: tmsstatsnodb
tmsstatsnodb: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py statsnodb

.PHONY: tmscreatequeue
tmscreatequeue: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py createqueue

.PHONY: tmsdeletequeue
tmsdeletequeue: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py deletequeue

.PHONY: tmscreatetiles
tmscreatetiles: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py createtiles

.PHONY: tmsqueuestats
tmsqueuestats: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tms_writer.py queuestats

.PHONY: tilejson
tilejson: configs/terrain/database.cfg configs/terrain/tms.cfg
	$(PYTHON_CMD) scripts/tilejson_writer.py $(TILEJSON_TEMPLATE)

.PHONY: clean
clean:
	rm -f configs/terrain/database.cfg
	rm -f configs/terrain/tms.cfg
	rm -f configs/raster/database.cfg

.PHONY: cleanall
cleanall: clean
	rm -rf venv
	rm -rf *.egg-info
	rm -f .tmp/*.*
