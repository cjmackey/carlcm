#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR/..

nosetests --with-coverage --cover-package=carlcm --cover-erase --cover-inclusive --cover-html --cover-html-dir=coverage --cover-branches $@
