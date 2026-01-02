Listener: Fixed an issue when using the wildcard binding address on Linux,
by specified type=socket.SOCK_STREAM and flags=socket.AI_PASSIVE when
calling socket.getaddrinfo() to resolve the specified host and port.
