#!/bin/sh
SCVER=`python -c 'import solvcon; print solvcon.__version__'`
# build source distribution file.
scons
rm -rf build/ lib/
python2.7 setup.py sdist
# build scdata.
tar cfz dist/scdata-$SCVER.tgz scdata/mesh/*.neu.gz
# build the project.
cd dist
rm -rf SOLVCON-$SCVER
tar xfz SOLVCON-$SCVER.tar.gz
cd SOLVCON-$SCVER
python2.7 setup.py build_ext --inplace
# test.
nosetests
