Development: Migrated from setup.py to pyproject.toml since that is the
recommended direction for Python packages. The make targets have not changed
(with the exception of the make targets 'buildc', 'installc', and 'testc'
for a cythonized distribution archive).
The content of the wheel and source distribution archives has not changed.

Some files have been renamed:
- minimum-constraints.txt to minimum-constraints-develop.txt
- .safety-policy-all.yml to .safety-policy-develop.yml

The version is now maintained automatically in 'pywbem/_version_scm.py'
which is not tracked in git and is created/updated when building the
distribution archives.
