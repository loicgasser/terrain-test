VENV = venv
PYTHON_CMD = $(VENV)/bin/python
FLAKE8_CMD = $(VENV)/bin/flake8
AUTOPEP8_CMD = $(VENV)/bin/autopep8
MAKO_CMD = $(VENV)/bin/mako-render
PREFIX ?= 1/
PYTHON_FILES := $(shell find forge/ -name '*.py')
USERNAME := $(shell whoami)

MAX_LINE_LENGTH=130
PEP8_IGNORE="E128,E221,E241,E251,E272,E711"

# E128: continuation line under-indented for visual indent
# E221: multiple spaces before operator
# E241: multiple spaces after ':'
# E251: multiple spaces around keyword/parameter equals
# E272: multiple spaces before keyword
# E711: comparison to None should be 'if cond is None:' (SQLAlchemy's filter syntax requires this ignore!)

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
	@echo "- updatesubmodule    Update 3d testapp"
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
	@echo "- tmspyramid         Create the TMS pyramid based on the config file tms.cfg"
	@echo "- tmsmetadata        Create the layers.json file"
	@echo "- tmsstats           Provide statistics about the TMS pyramid"
	@echo "- tmsstatsnodb       Provide statistics about the TMS pyramid, without db stats"
	@echo "- tmscreatequeue     Creates AWS SQS queue with given settings (all tiles)"
	@echo "- tmstmsdeletequeue  Deletes current AWS SQS queue (you loose everything)"
	@echo "- tmstmsqueuestats   Get stats of AWS SQS queue"
	@echo "- tmsttmscreatetiles Create tilses using the AWS SQS queue"
	@echo "- clean              Clean all generated files and folders"
	@echo
	@echo "Variables:"
	@echo
	@echo "- USERNAME (current value: $(USERNAME))"
	@echo "- PYTHON_CMD (current value: $(PYTHON_CMD))"
	@echo "- FLAKE8_CMD (current value: $(FLAKE8_CMD))"
	@echo "- AUTOPEP8_CMD (current value: $(AUTOPEP8_CMD))"
	@echo


.PHONY: all
all: install apache/testapp.conf database.cfg tms.cfg logging.cfg test lint

.PHONY: install
install:
	virtualenv $(VENV) --system-site-packages
	$(PYTHON_CMD) setup.py develop

apache/testapp.conf: apache/testapp.conf.mako
	$(MAKO_CMD) --var "user=$(USERNAME)" --var "directory=$(CURDIR)" $< > $@

database.cfg: database.cfg.mako
	$(MAKO_CMD) --var "pgpass=$(PGPASS)" --var "dbtarget=$(DBTARGET)" --var "username=$(USERNAME)" $< > $@

tms.cfg: tms.cfg.mako
	$(MAKO_CMD) --var "bucketname=$(BUCKETNAME)" --var "profilename=$(PROFILENAME)" $< > $@

logging.cfg: logging.cfg.mako
	$(MAKO_CMD) --var "logfilefolder=$(LOGFILEFOLDER)" $< > $@

.PHONY: test
test:
	$(VENV)/bin/nosetests forge/tests/

.PHONY: lint
lint:
	$(FLAKE8_CMD) --max-line-length=${MAX_LINE_LENGTH} --ignore=${PEP8_IGNORE} forge/

.PHONY: autolint
autolint:
	@echo $(PYTHON_FILES)
	$(AUTOPEP8_CMD) -v -i -a --max-line-length=${MAX_LINE_LENGTH} --ignore=${PEP8_IGNORE} $(PYTHON_FILES)

.PHONY: updatesubmodule
updatesubmodule:
	git submodule update
	git submodule foreach git pull origin master

.PHONY: console
console:
	$(PYTHON_CMD) forge/scripts/db_management.py console

.PHONY: create
create:
	$(PYTHON_CMD) forge/scripts/db_management.py create

.PHONY: createuser
createuser:
	$(PYTHON_CMD) forge/scripts/db_management.py createuser

.PHONY: createdb
createdb:
	$(PYTHON_CMD) forge/scripts/db_management.py createdb

.PHONY: setupfunctions
setupfunctions:
	$(PYTHON_CMD) forge/scripts/db_management.py setupfunctions

.PHONY: populate
populate:
	$(PYTHON_CMD) forge/scripts/db_management.py populate

.PHONY: populatelakes
populatelakes:
	$(PYTHON_CMD) forge/scripts/db_management.py populatelakes

.PHONY: dropuser
dropuser:
	$(PYTHON_CMD) forge/scripts/db_management.py dropuser

.PHONY: dropuser
dropdb:
	$(PYTHON_CMD) forge/scripts/db_management.py dropdb

.PHONY: destroy
destroy:
	$(PYTHON_CMD) forge/scripts/db_management.py destroy

.PHONY: counttiles
counttiles:
	$(PYTHON_CMD) forge/scripts/s3_tiles.py -p $(PREFIX) count

.PHONY: deletetiles
deletetiles:
	$(PYTHON_CMD) forge/scripts/s3_tiles.py -p $(PREFIX) delete

.PHONY: listtiles
listtiles:
	$(PYTHON_CMD) forge/scripts/s3_tiles.py -p $(PREFIX) list

.PHONY: tmspyramid
tmspyramid:
	$(PYTHON_CMD) forge/scripts/tms_writer.py create

.PHONY: tmsmetadata
tmsmetadata:
	$(PYTHON_CMD) forge/scripts/tms_writer.py metadata

.PHONY: tmsstats
tmsstats:
	$(PYTHON_CMD) forge/scripts/tms_writer.py stats

.PHONY: tmsstatsnodb
tmsstatsnodb:
	$(PYTHON_CMD) forge/scripts/tms_writer.py statsnodb

.PHONY: tmscreatequeue
tmscreatequeue:
	$(PYTHON_CMD) forge/scripts/tms_writer.py createqueue

.PHONY: tmsdeletequeue
tmsdeletequeue:
	$(PYTHON_CMD) forge/scripts/tms_writer.py deletequeue

.PHONY: tmscreatetiles
tmscreatetiles:
	$(PYTHON_CMD) forge/scripts/tms_writer.py createtiles

.PHONY: tmsqueuestats
tmsqueuestats:
	$(PYTHON_CMD) forge/scripts/tms_writer.py queuestats


.PHONY: clean
clean:
	rm -rf venv
	rm -rf *.egg-info
	rm -rf 3d-testapp
	rm -f apache/testapp.conf
	rm -f database.cfg
	rm -f tms.cfg
	rm -f logging.cfg
	rm -f .tmp/*.*
