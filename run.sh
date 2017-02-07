#!/bin/sh

python3 collection.py 2>&1 | tee foo.log; echo; echo; echo; echo; grep -v ^DEBUG foo.log
