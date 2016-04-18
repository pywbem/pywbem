#!/bin/bash
# Send an indication to a local WBEM listener

# To use HTTPS, create a self-signed certificate with private key:
#   openssl req -new -x509 -keyout tmp.pem -out tmp.pem -days 365 -nodes

# To start the WBEM listener, use, in a different terminal session:
#   PYTHONPATH=. examples/listen.py 127.0.0.1 5000 5001 tmp.pem tmp.pem

ssl=1  # Use HTTPS

http_port="5000"
https_port="5001"
host="127.0.0.1"
cert_file="tmp.pem"
key_file="tmp.pem"

if [[ "$ssl" == "1" ]]; then
  url="https://${host}:${https_port}"
  key_opts="--insecure --key $key_file --cert $cert_file"
else
  url="http://${host}:${http_port}"
  key_opts=""
fi

data='<CIM CIMVERSION="2.0" DTDVERSION="2.4">
  <MESSAGE ID="42" PROTOCOLVERSION="1.4">
    <SIMPLEEXPREQ>
      <EXPMETHODCALL NAME="ExportIndication">
        <EXPPARAMVALUE NAME="NewInstance">
          <INSTANCE CLASSNAME="CIM_AlertIndication">
            <PROPERTY NAME="Severity" TYPE="string">
              <VALUE>high</VALUE>
            </PROPERTY>
          </INSTANCE>
        </EXPPARAMVALUE>
      </EXPMETHODCALL>
    </SIMPLEEXPREQ>
  </MESSAGE>
</CIM>'

curl_opts="$key_opts --verbose --show-error --header 'Content-Type: text/xml' --data '${data}'"

cmd="curl $url $curl_opts"
echo -e "Request payload:\n$data"

eval $cmd
echo ""

