#!/bin/bash
#
#  Compile a mof file into a WBEMServer environment
#  The server and mof default to a local server with http and no
#  secrity
#
function USAGE {
cat << EOF
Usage: `basename $0` <parameters> ;

parameters:
    -h --help       Output the help information on this script and exit
    -u --url        Url of WBEM Server. default: http://localhost
    -u --user       Server user name (default: None
    -p --password   Server password
    -m --mof        Mof file to compile (default test.mof)
    -nvc --no_verify_cert
    -n --namespace  Namespace in which to insert the mof. default root/cimv2
    -r --remove     Remove the elements in the mof file defined from the
                    server if they exist in the server.
    -v              Verbose display   
EOF
}

SERVER_URL="http://localhost"
MOF_TO_COMPILE="test.mof"
NAMESPACE='--namespace root/cimv2'
USER=""
PASSWORD=""
VERIFY="--no-verify-cert"
REMOVE=""

##############################################################
## Scan input parameters
#############################################################
while test -n "$1"; do
    case "$1" in
    --help|-h)
        USAGE
        exit 1
    ;;

    -s|--server)
        if [ "$2" == "" ]; then
            echo value required for parameter $1
            exit 1
        fi
        SERVER_URL=$2
        shift
    ;;
    -n|--namespace)
        if [ "$2" == "" ]; then
            echo value required for parameter $1
            exit 1
        fi
        NAMESPACE="--namespace "$2
        shift
    ;;

    -m|--mof)
        if [ "$2" == "" ]; then
            echo value required for parameter $1
            exit 1
        fi
        MOF_TO_COMPILE=$2
        shift
    ;;

    -V|--verify)
        VERIFY=""

    ;;
        
    -u|--user)
        if [ "$2" == "" ]; then
            echo value required for parameter $1
            exit 1
        fi
        USER="=--user "$2
        shift
    ;;
        
    -p|--password)
        if [ "$2" == "" ]; then
            echo value required for parameter $1
            exit 1
        fi
        PASSWORD= "--password " $2
        shift
    ;;
        
    -r|--remove)
        REMOVE="--remove"
    ;;        
       
    -v|--verbose)
        VERBOSE="--verbose"
    ;;
        
    *)
        echo "Unknown argument $1"
        USAGE
        exit 1
    ;;

    esac
    shift
done
 echo "mof_compiler --server" $SERVER_URL $NAMESPACE $PASSWORD $USER $VERIFY $REMOVE $MOF_TO_COMPILE
mof_compiler --server $SERVER_URL $NAMESPACE $PASSWORD $USER $VERIFY $REMOVE $MOF_TO_COMPILE
if [ "$?" != "0" ]; then
    echo "mof compiler error return" $?
fi
