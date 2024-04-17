#!/usr/bin/env bash

ROOT=/work/

cd $ROOT || exit 1

opuscleaner-server serve --reload
