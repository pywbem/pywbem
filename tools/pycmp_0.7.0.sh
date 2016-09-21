#!/bin/bash
# Simply invoke this script in root directory of the repo, without any args

opts=$*

version="0.7.0"
distfile="dist/pywbem-0.7/pywbem-${version}.tar.gz"

pycmp="tools/pycmp.py"

if [[ ! -f $pycmp ]]; then
  echo "Error: Comparison script not found: $pycmp"
  echo "       Maybe you invoked this script from the wrong directory?"
  exit 1
fi

if [[ ! -f $distfile ]]; then
  echo "Error: PyWBEM distribution archive not found: $distfile"
  echo "       Maybe you invoked this script from the wrong directory?"
  exit 1
fi

echo "Generating report about symbol changes since PyWBEM $version"

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

# twisted is needed for pywbem/twisted_client.py
pip install twisted

$pycmp -e -i $opts $tmpdir/pywbem pywbem >$reportfile

echo "Success: Generated report: $reportfile"
