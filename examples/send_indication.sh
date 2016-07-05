#!/bin/bash
# Send  indications to a WBEM listener. 
# See USAGE for cmd line parameter details.  

# To use HTTPS, create a self-signed certificate with private key:
#   openssl req -new -x509 -keyout tmp.pem -out tmp.pem -days 365 -nodes

# To start the WBEM listener, use, in a different terminal session:
#   PYTHONPATH=. examples/listen.py 127.0.0.1 5000 5001 examples/tmp.pem examples/tmp.pem

function USAGE {
cat << EOF
Usage: `basename $0` url <options> ;
    Send indications to a WBEM listener define by url and port.
    Sends the number of indications defined by -d parameter.

    url  - url of listener including schema (default: http://127.0.0.1)
           or https://<hostname>

    Where the options are:
    -h --help               Usage 

    -p --port    integer    Listener port (default; 5000)
    -c --cert    file_name  Certificate file (default; None)
    -k --key     file_name  Key file (default; None)
    -d --deliver count      Number of indications to deliver (default; 1)
EOF
}

# default cmd line options

port="5000"
cert_file=""
key_file=""
NUMBER_TO_DELIVER=1
URL="http://127.0.0.1"

while test -n "$1"; do
    case "$1" in
        --help|-h)
            USAGE
            exit 1
            ;;
        -p|--port)
            port="$2"
            shift
            ;;
        -c|--certfile)
            cert_file="$2"
            shift
            ;;
        -k|--keyfile)
            key_file="$2"
            shift
            ;;
        -d|--deliver)
            NUMBER_TO_DELIVER="$2"
            shift
            ;;
        *)
            echo all $1
            if [[ $1 =~ "http" ]] ; then
                URL=$1
            else
                echo unrecognized parameter $1. Terminating
                exit 1
                USAGE
            fi
            ;;
    esac
    shift # past argument or value
done

if [[ $URL =~ "https" ]] ; then
  fullurl="$URL:${port}"
  key_opts="--insecure --key $key_file --cert $cert_file"
else
  fullurl="$URL:${port}"
  key_opts=""
fi

echo fullurl=$fullurl key_opts=$key_opts

# loop to deliver the number of indications defined by
# number_to_deliver

START_TIME=$(date +%s)
SEQ_NUMBER=0
while [ $SEQ_NUMBER -lt $NUMBER_TO_DELIVER ]; do

    let SEQ_NUMBER=SEQ_NUMBER+1
    
    CUR_TIME=$(date +%s)
    DELTA_TIME=$((CUR_TIME-$START_TIME))
    data='<?xml version="1.0" encoding="utf-8" ?>
    <CIM CIMVERSION="2.0" DTDVERSION="2.4">
      <MESSAGE ID="42" PROTOCOLVERSION="1.4">
        <SIMPLEEXPREQ>
          <EXPMETHODCALL NAME="ExportIndication">
            <EXPPARAMVALUE NAME="NewIndication">
              <INSTANCE CLASSNAME="CIM_AlertIndication">
                <PROPERTY NAME="Severity" TYPE="string">
                  <VALUE>high</VALUE>
                </PROPERTY>
                <PROPERTY NAME="Sequence_Number" TYPE="string">
                  <VALUE>'$SEQ_NUMBER'</VALUE>
                </PROPERTY>
                <PROPERTY NAME="DELTA_TIME" TYPE="string">
                  <VALUE>'$DELTA_TIME'</VALUE>
                </PROPERTY>
              </INSTANCE>
            </EXPPARAMVALUE>
          </EXPMETHODCALL>
        </SIMPLEEXPREQ>
      </MESSAGE>
    </CIM>'

    curl_opts="$key_opts --verbose --show-error --header 'Content-Type: text/xml' --data '${data}'"

    cmd="curl $fullurl $curl_opts"
    echo -e "Request payload:\n$data"

    eval $cmd
    echo send $SEQ_NUMBER of $NUMBER_TO_DELIVER
done

echo ""

