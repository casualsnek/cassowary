#!/usr/bin/env bash
rm -rf ./dist
rm -rf ./src/*.egg-info
python3 -m build
