#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

UXPLAY_BUILD_DIR=$SCRIPT_DIR/../submodules/UxPlay/build
UXPLAY_DIR=$SCRIPT_DIR/../uxplay
UXPLAY_BIN_DIR=$UXPLAY_DIR/bin

mkdir -p $UXPLAY_BUILD_DIR
pushd $UXPLAY_BUILD_DIR
cmake ..
make
version=$(./uxplay -h 2>&1 | head -n1 | grep -oP '\d+\.\d+\.\d+')
popd

mkdir -p $UXPLAY_BIN_DIR
cp $UXPLAY_BUILD_DIR/uxplay $UXPLAY_BIN_DIR

pushd $UXPLAY_DIR
tar -czvf uxplay-linux-v$version.tar.gz bin/