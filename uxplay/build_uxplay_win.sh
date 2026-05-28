#!/usr/bin/env bash
set -e
pacman -Syu --noconfirm --needed mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-libplist mingw-w64-ucrt-x86_64-gstreamer mingw-w64-ucrt-x86_64-gst-plugins-base p7zip
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

UXPLAY_BUILD_DIR=$SCRIPT_DIR/../submodules/UxPlay/build
UXPLAY_DIR=$SCRIPT_DIR/../uxplay
UXPLAY_BIN_DIR=$UXPLAY_DIR/bin
UXPLAY_LIB_DIR=$UXPLAY_DIR/lib

mkdir -p $UXPLAY_BUILD_DIR
pushd $UXPLAY_BUILD_DIR
cmake ..
ninja
cmake --install . --prefix $HOME/../../ucrt64
version=$(uxplay.exe -h 2>&1 | head -n1 | grep -oP '\d+\.\d+\.\d+')
popd

mkdir -p $UXPLAY_BIN_DIR $UXPLAY_LIB_DIR
cp $UXPLAY_BUILD_DIR/uxplay $UXPLAY_BIN_DIR
cp -R /ucrt64/lib/gstreamer-1.0 $UXPLAY_LIB_DIR


echo "Copying uxplay.exe direct dependencies"
ldd /ucrt64/bin/uxplay.exe | grep -i ucrt64 | awk '{print $3}' | while IFS= read -r path; do
    printf "\rCopying: %-60s" "$(basename $path)"
    cp "$path" $UXPLAY_BIN_DIR
done

printf "\rCopying gstreamer library dependencies\n"
for dll in /ucrt64/lib/gstreamer-1.0/*.dll; do
    ldd "$dll" | grep -i ucrt64 | awk '{print $3}' | while IFS= read -r path; do
        printf "\rCopying: %-60s" "$(basename $path)"
        cp "$path" $UXPLAY_BIN_DIR
    done
done

echo ""

pushd $UXPLAY_DIR
7z a -tzip -mx=9 uxplay-win64-v$version.zip bin/ lib/