Development of PyWBEM Client
============================

Git workflow
------------

* Long-lived branches:
  - `master` - for next functional release
  - `stable_M.N` - for next fix release on fix stream `M.N`.
* We use topic branches for everything!
  - Based upon the intended long-lived branch, if no dependencies
  - Based upon an earlier topic branch, in case of dependencies
  - It is valid to rebase topic branches and force-push them.
* We use pull requests to review the branches.
  - Use the correct long-lived branch (e.g. `master` or `stable_0.8`) as a
    merge target!
  - Review happens as comments on the pull requests.
  - At least two +1 are required for merging.
* GitHub meanwhile offers different ways to merge pull requests. We merge pull
  requests by creating merge commits, so the single commits of a topic branch
  remain unchanged, and we see the title line of the pull request in the merge
  commit message, which is often the only place that tells the issue that was
  fixed.

Releasing a version
-------------------

This section describes how to release a version of pywbem to Pypi.

The description assumes that the `pywbem/pywbem` repo and the
`pywbem/pywbem.github.io` repo are both cloned locally in sibling directories
named `pywbem` and `pywbem.github.io`.

The upstream repos are assumed to have the remote name `origin`.

A shell variable `$MNU` is used in the description to refer to the `M.N.U`
version (e.g. `0.9.0`) that is to be released.

1.  Switch to your work directory of the `pywbem/pywbem` repo (this is where
    the `makefile` is), and perform the following steps in that directory.

2.  Set shell variables for the version to be released:

    - `MNU='0.9.0'`
    - `MN='0.9'`

3.  Check out the `master` branch (because that will be the basis for the
    topic branch used to release the package), and update it from upstream:

    - `git checkout master`
    - `git pull`

4.  Create a topic branch for the release, based upon the `master` branch:

    - `git checkout -b release_$MNU`

5.  Edit the change log to reflect all changes in the release:

    - `vi docs/changes.rst`

    This can be done by comparing with the commit log of the master branch
    back to the previous version.

6.  Edit the README file to remove any release planning info for the current
    release and to add some preliminary release planning info for the next
    release:

    - `vi README.md`

7.  Finalize the package versions in the following files by changing the
    development version `M.N.U.dev0` to the final version `M.N.U`:

    - `vi pywbem/_version.py`
    - `vi docs/changes.rst`

    Note: The `makefile`, `setup.py` and `docs/conf.py` determine the package
    version at run time from `pywbem/__init__.py`, so they do not need to be
    updated.

8.  Perform a complete build (in your favorite Python virtual environment):

    - `make clobber all`

    If this fails, fix and iterate over this step until it succeeds.

    Note: This is for a quick turnaround when fixing issues. In Step 12, Tox is
    used to run `make test` in multiple Python environments, for a complete
    Python environment coverage.

9.  Commit the changes and push to upstream:

    - `git commit -a -m "Release v$MNU"`
    - `git push --set-upstream origin release_$MNU`

10. On Github, create a Pull Request for branch `release-$MNU`. This will
    trigger the CI runs (e.g. Travis, Appveyor).

    **Important:** Regardless of which branch the commit was based upon, GitHub
    will by default target the `master` branch for the merge. This is correct
    for what we do here.

11. Perform a complete test using Tox:

    - `tox`

    This single command will run `make test` in all supported Python
    environments.

12. Perform an install test:

    - `cd testsuite; ./test_install.sh`

    Note: The changed directory is necessary so that the locally available
    package directory is not used.

13. Perform a test in a CI environment (Andy):

    - Post the results to the release PR.

14. Perform a test against a real WBEM server (Karl):

    - Post the results to the release PR.

15. If any of the tests (including the CI runs of the Pull Request)
    fails, fix the problem and iterate back to step 8. until they all succeed.

16. Once all tests and the CI runs for the Pull Request succeed:

    - Merge the Pull Request on GitHub (no review is needed)
    - Delete the Pull Request on GitHub

    Note: This cannot be done before the CI runs succeed. 

17. Checkout the `master` branch and update it from upstream:

    - `git checkout master`
    - `git pull`

18. Clean up local branches that have been merged:

    - `git-prune origin` (From `andy-maier/gitsurvival`)

19. Tag the release:

    - It is important to do this only with an up-to-date `master` branch
      checked out (see step 17).

    - If a tag for the new release already exists for some reason, delete it
      and push the deletion upstream:

      - `git tag -l v$MNU |xargs git tag -d`
      - `git push --tags`

    - Create a tag for the new release and push the addition upstream:

      - `git tag v$MNU`
      - `git push --tags`

20. If this is a new minor release, create a branch for its fix stream:

    - `git checkout -b stable_$MN`
    - `git push --set-upstream origin stable_$MN`

21. On RTD, activate the new branch `stable_$MN` as a version to be built.

22. On GitHub, edit the new tag, and create a release description on it. This
    will cause it to appear in the Release tab.

23. On GitHub, close milestone `M.N.U`.

24. Upload the package to PyPI:

    **Attention!!** This only works once. You cannot re-release the same
    version to PyPI.

    - `make upload`

    Verify that it arrived on PyPI: https://pypi.python.org/pypi/pywbem/

25. Switch to the directory of the `pywbem.github.io` repo and perform the
    following steps from that directory:

    - `cd ../pywbem.github.io`

26. Check out the `master` branch (on `pywbem.github.io`, we only have that one
    long-lived branch), and update it from upstream:

    - `git checkout master`
    - `git pull`

27. Update the download table in `pywbem/installation.html` for the new
    release:

    - `vi pywbem/installation.html`

    For a new M.N release, insert a new row.

    For a new M.N.U release on an existing M.N release, update the row for the
    M.N.U-1 release.

28. Verify that the installation page (`pywbem/installation.html` in your web
    browser) shows the new release correctly, and that all of its links work.

29. Commit the changes and push to the upstream repo (we dont use a topic
    branch for this):

    - `git add --all`
    - `git commit -m "Release v$MNU"`
    - `git push`

30. Verify that the
    [PyWBEM installation page](http://pywbem.github.io/pywbem/installation.html)
    has been updated, and that all the links work and show the intended
    version.

31. Announce the new release on the
    [pywbem-devel mailing list](http://sourceforge.net/p/pywbem/mailman/pywbem-devel/).

Starting a new version
----------------------

This section shows the steps for starting development of a new version.

A shell variable `$MNU` is used in the description to refer to the `M.N.U`
version (e.g. `0.10.x`) whose development is started.

1.  Switch to the directory of the `pywbem` repo, and perform the following
    steps in that directory.

2.  Set a shell variable for the new version to be developed:

    - `MNU='0.10.0'`

3.  Check out the branch the new version should be based upon: Normally, that
    would be the `master` branch (shown in the example); for fixing an older
    version, that would be its `stable_X.Y.Z` branch. Update that branch from
    upstream:

    - `git checkout master`
    - `git pull`

4.  Create a topic branch for the new version:

    - `git checkout -b start_$MNU`

5.  Increase the package versions in the following files by changing the
    old final version `M.N.U-1` to the new development version `M.N.U.dev0`:

    - `vi pywbem/_version.py`
    - `vi docs/changes.rst`

    Note: The `makefile`, `setup.py` and `docs/conf.py` determine the package
    version at run time from `pywbem/__init__.py`, so they do not need to be
    updated.

6. Commit the changes and push to upstream:

    - `git commit -a -m "Start development of v$MNU"`
    - `git push --set-upstream origin start_$MNU`

7.  On Github, create a Pull Request for the `start_$MNU` branch. This will
    trigger the CI runs (e.g. Travis, Appveyor).

    **Important:** Regardless of which branch the commit was based upon, GitHub
    will by default target the `master` branch for the merge. Change that to
    the branch you checked out in step 3.

8.  If the CI runs fail (should not happen) fix it and go back to step
    6, until it succeeds.

9.  Once the CI runs for this PR succeed:

    - Merge the PR on GitHub (no review is needed)
    - Delete the PR on GitHub

    Note: This cannot be done before the CI runs succeed.

10. Checkout the `master` branch and update it from upstream:

    - `git checkout master`
    - `git pull`

11. Clean up local branches that have been merged:

    - `git-prune origin` (From `andy-maier/gitsurvival`)

12. On GitHub, create a new milestone `M.N.U`.

13. On GitHub, list all open issues that still have a milestone of less than
    `M.N.U` set, and update them to target milestone `M.N.U`.

Use of Python namespaces
========================

This section describes how Python namespaces are used by the pywbem package.

There is obviously a history of namespace usage in pywbem that is different,
and that we try to still support for compatibility. This section describes both
the future use and the historical use.

The pywbem package corresponds 1:1 to:

* GitHub repository `pywbem/pywbem`
* Pypi package `pywbem`
* Python namespace `pywbem` and its sub-namespaces.

The following namespaces are used (as of v0.9.0):

* `pywbem`: WBEM client API, WBEM indication API.

  It provides the traditional PyWBEM stuff, minus the MOF compiler and any
  stuff that was moved to the attic (e.g. `cim_provider`):

  Note that the `irecv` namespace was always experimental and will be go to
  the attic.

  For backwards compatibility, some content of this namespace is also available
  in the historical `pywbem.cim_obj` etc. namespaces.

* `pywbem.mof_compiler`: MOF compiler API.

   It provides:

   - `MOFCompiler` class etc.
