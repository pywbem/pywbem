"""
    Display the cli input arguments with their names
"""
attrs = vars(ARGS)
print('\n'.join("%s: %s" % item for item in attrs.items()))
