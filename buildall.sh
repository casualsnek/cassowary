#!/usr/bin/env bash
echo "==> Building linux component"
cd ./app-linux
build.sh
echo "==> Done"
cd ..
cd "==> Building windows component"
cd ./app-win
build.sh
echo "==> Done"
