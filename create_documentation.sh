#!/usr/bin/env bash
pushd docs
pip3 install -r requirements.txt
make clean && make html
echo "Documentation can be found under docs/build"
popd
