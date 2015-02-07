#!/bin/bash

cd "$( dirname "${BASH_SOURCE[0]}" )"/..

time nosetests --with-coverage --cover-package=carlcm --cover-erase --cover-inclusive --cover-html --cover-html-dir=coverage --cover-branches --no-byte-compile --with-doctest $@
