#!/usr/bin/env bash
# Download python3 and set it up in wine environment
checksum=""
download_python()
{
  if [ ! -f /tmp/pysetup.exe ]
  then
      echo "Downloading python"
      wget https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe -O /tmp/pyseup.exe
  fi
  checksum="$(md5sum /tmp/pysetup.exe | awk '{ print $1 }')"
}
main()
{
if [ "$checksum" == "ac25cf79f710bf31601ed067ccd07deb" ]; then
    # Install python and run build script
    echo "Installing python 3.9.6. into wine env at '/tmp/cassowary-build'"
    export WINEPREFIX=/tmp/cassowary-build
    wine /tmp/pysetup.exe /quiet PrependPath=1 Include_pip=1 Include_test=0 AssociateFiles=0 Include_launcher=0
    wine build.bat
    echo "Build complete"
else
    echo "Checksum of python installer do not match!"
    download_python
    main
fi
}
main

