#
#  Demo of python scripts with wbemcli
#
#  This pair of scripts just starts wbemcli, displays the command line
#  arguments args and exits wbemcli
#  It works as a simple demo because it does not actually call the server
#  with an operation so does not understand if there is actually no
#  running server.
#
wbemcli http://localhost -s wbemcli_display_args.py wbemcli_quit.py
