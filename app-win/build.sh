#!/usr/bin/env bash
# Download python3 and set it up in wine environment
checksum=""
min_build_for=${MIN_WIN_VER:-win7}
checksum_verification=${VERITY_DOWNLOADS:-0}
export WINEPREFIX=/tmp/cassowary-build
mkdir -p /tmp/cassowary-build
download_python()
{
  if [ ! -f /tmp/pysetup.exe ]
  then
      echo "Downloading python"
        if [ "$min_build_for" == "win7" ]; then
            echo "Keeping Windows 7 as minimum requirement"
            wine winecfg -v win7
            wget https://www.python.org/ftp/python/3.7.4/python-3.7.4-amd64.exe -O /tmp/pysetup.exe
        else
            echo "Keeping Windows 10 as minimum requirement"
            wine winecfg -v win10
            wget https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe -O /tmp/pysetup.exe
        fi
  fi
  checksum="$(md5sum /tmp/pysetup.exe | awk '{ print $1 }')"
}
main()
{
if [ "$checksum" == "ac25cf79f710bf31601ed067ccd07deb" ] || [ "$checksum" == "531c3fc821ce0a4107b6d2c6a129be3e" ] || [ "$checksum_verification" == "0" ] ; then
    # Install python and run build script
    echo "Installing python in wine env at '/tmp/cassowary-build'. Target Min Windows version: $min_build_for"
    wine /tmp/pysetup.exe /quiet PrependPath=1 Include_pip=1 Include_test=0 AssociateFiles=0 Include_launcher=0
    wine build.bat
    echo "Build complete"
    rm /tmp/pysetup.exe
else
    echo "Checksum of python installer ( $checksum ) do not match!"
    download_python
    main
fi
}
download_python
main

