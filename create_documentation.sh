#!/usr/bin/env bash
pushd docs
pip install -r requirements.txt
make clean && make html
echo "Documentation can be found under docs/build"
popd
