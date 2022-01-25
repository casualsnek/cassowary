#!/usr/bin/env bash
echo "==> Building linux component"
cd app-linux
./build.sh
echo "==> Done"
cd ..
echo "==> Building windows component"
cd app-win
./build.sh
echo "==> Done"
