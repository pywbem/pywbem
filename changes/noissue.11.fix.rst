Development: Fixed failure of 'check_reqs' make target that was caused by a new
version of the 'jupyter' package that is no longer importable, by replacing
it in the 'check_reqs' make target with the 'ipywidgets' and 'jupyter_console'
packages. This also improved the checking for missing packages, and new
packages were added to the minimum constraints file.
