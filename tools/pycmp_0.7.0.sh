#!/bin/bash
echo "Generating report about symbol changes since pywbem 0.7.0"

version="0.7.0"
distfile="dist/pywbem-0.7/pywbem-${version}.tar.gz"
reportfile=pycmp_${version}.log

tmpdir=tmp_pycmp_$version
if [[ -d $tmpdir ]]; then
  rm -rf $tmpdir
fi
mkdir $tmpdir
tar -x -f $distfile -C $tmpdir
mkdir $tmpdir/pywbem
mv $tmpdir/pywbem-${version}/*.py $tmpdir/pywbem/
rm $tmpdir/pywbem/setup.py   # not part of the package
rm $tmpdir/pywbem/wbemcli.py # cannot be imported, in 0.7.0
tools/pycmp.py -e $tmpdir/pywbem pywbem >$reportfile
echo "Success: Generated report: $reportfile"
