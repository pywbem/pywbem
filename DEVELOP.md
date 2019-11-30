Releasing PyWBEM
================

Git workflow
------------

* Long-lived branches:
  - `master` - for next functional version
  - `stable_M.N` - for fix stream of released version `M.N`.
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

This section describes how to release a version of pywbem to PyPI.

It covers all variants of versions:

* Releasing the master branch as a new (major or minor) version
* Releasing a fix stream branch of an already released version as a new fix
  version

The description assumes that the `pywbem/pywbem` repo and the
`pywbem/pywbem.github.io` repo are both cloned locally in sibling directories
named `pywbem` and `pywbem.github.io`.
Their upstream repos are assumed to have the remote name `origin`.

1.  Switch to your work directory of the `pywbem/pywbem` repo (this is where
    the `makefile` is), and perform the following steps in that directory.

2.  Set shell variables for the version and branch to be released:

    - `MNU="0.9.0"` or `MNU="0.8.1"` - Full version number `M.N.U`
    - `MN="0.9"` or `MN="0.8"` - Major and minor version number `M.N`
    - `BRANCH="master"` or `BRANCH="stable_$MN"`

3.  Check out the branch to be released, make sure it is up to date with
    upstream, and create a topic branch for the version to be released:

    - `git checkout $BRANCH`
    - `git pull`
    - `git checkout -b release_$MNU`

4.  Edit the version file and set the version to be released:

    - `vi pywbem/_version.py`

    `__version__ = 'M.N.U'`

    Where `M.N.U` is the version to be released, e.g. `0.8.1`.

    You can verify that this version is picked up by setup.py as follows::

    ```
    ./setup.py --version
    0.8.1
    ```

5.  Edit the change log:

    - `vi docs/changes.rst`

    To make the following changes for the version to be released:

    * Finalize the version to the version to be released.

    * Remove the statement that the version is in development.

    * Update the statement which fixes of the previous stable version
      are contained in this version.  If there is no fix release
      of the previous stable version, the line can be removed.

    * Change the release date to today´s date.

    * Make sure that all changes are described. This can be done by comparing
      the changes listed with the commit log of the master branch.

    * Make sure the items in the change log are relevant for and understandable
      by users of pywbem.

    * In the "Known issues" list item, remove the link to the issue tracker
      and add text for any known issues you want users to know about.

      Note: Just linking to the issue tracker quickly becomes incorrect for a
      released version and is therefore only good during development of a
      version. In the "Starting a new version" section, the link will be added
      again for the new version.

6.  Edit the README file:

    - `vi README.rst`

    To make the following changes:

    * Update the constants near the top of the file::

      ```
      .. |pywbem-version| replace:: {M.N.U}
      .. |pywbem-next-version| replace:: {M.N.U+1}
      .. |pywbem-next-issue| replace:: {issue-number}
      ```

      Where the items in curly braces are replaced with their actual values.

7.  Edit the README_PYPI file:

    - `vi README_PYPI.rst`

    To make the following changes:

    * Update the constants near the top of the file::

      ```
      .. |pywbem-version-mn| replace:: {M.N}
      ```

      Where the items in curly braces are replaced with their actual values.

8.  Perform a complete build (in your favorite Python virtual environment):

    - `make clobber`
    - `make all`

    If this fails, fix and iterate over this step until it succeeds.

9.  Commit the changes and push to upstream:

    - `git status` - to double check which files have been changed
    - `git commit -asm "Release $MNU"`
    - `git push --set-upstream origin release_$MNU`

10. On Github, create a Pull Request for branch `release_$MNU`. This will
    trigger the CI runs in Travis and Appveyor.

    Important: When creating Pull Requests, GitHub by default targets
    the `master` branch. If you are releasing a fix version, you need to
    change the target branch of the Pull Request to `stable_M.N`.

11. Optional: Perform a complete test using Tox:

    - `tox`

    This will create virtual Python environments for all supported versions
    and will invoke `make test` (with its prerequisite make targets) in each
    of them.

12. Optional: Perform a test in a local multi-platform test environment (Andy):

    - Post the results to the release PR.

13. Optional: Perform a test against a real WBEM server (Karl):

    - Post the results to the release PR.

14. If any of the tests mentioned above fails, fix the problem and iterate
    back to step 6. until they all succeed.

15. On GitHub, once the CI runs for the Pull Request succeed:

    - Merge the Pull Request (no review is needed)
    - Delete the branch of the Pull Request (`release_M.N.U`)

16. Checkout the branch you are releasing, update it from upstream, and
    delete the local topic branch you created:

    - `git checkout $BRANCH`
    - `git pull`
    - `git branch -d release_$MNU`

17. Tag the version:

    This step tags the local repo and pushes it upstream:

    - `git status` - double check that the branch to be released
      (`$BRANCH`) is checked out
    - `git tag $MNU`
    - `git push --tags`

18. If you released the `master` branch (for a new minor or major version),
    it will be fixed separately, so it needs a new fix stream.

    * Create a branch for its fix stream and push it upstream:

      - `git status` - double check that the branch to be released
        (`$BRANCH`) is checked out
      - `git checkout -b stable_$MN`
      - `git push --set-upstream origin stable_$MN`

    * Log on to [RTD](https://readthedocs.org/), go to the `pywbem` project,
      and activate the new branch `stable_M.N` as a version to be built.

19. On GitHub, edit the new tag, and create a release description on it. This
    will cause it to appear in the Release tab.

20. On GitHub, close milestone `M.N.U`.

    Note: Issues with that milestone will be moved forward in the section
    "Starting a new version".

21. Upload the package to PyPI:

    **Attention!!** This only works once. You cannot re-release the same
    version to PyPI.

    - `make upload`

    Verify that it arrived on PyPI: https://pypi.python.org/pypi/pywbem/

22. Switch to the directory of the `pywbem.github.io` repo and perform the
    following steps from that directory:

    - `cd ../pywbem.github.io`

23. Check out the `master` branch and update it from upstream:

    - `git checkout master`
    - `git pull`

    In this repo, we don´t use a topic branch for these changes.

24. Edit the installation page:

    - `vi pywbem/installation.html`

    To make the following changes in the installation table:

    * If you are releasing a new minor or major version, insert a new row.
    * If you are releasing a fix version, update the row for the release
      it replaces.

    Verify with a web browser on the locally changed file
    `pywbem/installation.html` that the new release shows up correctly,
    and that all of its links work.

25. Commit the changes and push to the upstream repo:

    - `git status` - to double check which files have been changed
    - `git commit -asm "Release $MNU"`
    - `git push`

26. Announce the new version on the
    [pywbem-devel mailing list](https://sourceforge.net/p/pywbem/mailman/pywbem-devel/).

Starting a new version
----------------------

This section shows the steps for starting development of a new version of pywbem.

It covers all variants of new versions:

* A new (major or minor) version for new development based upon the `master`
  branch
* A new fix version based on a `stable_M.N` fix stream branch.

1.  Switch to the directory of the `pywbem` repo, and perform the following
    steps in that directory.

2.  Set shell variables for the version to be started and for the branch it is
    based upon:

    - `MNU="0.10.0"` or `MNU="0.9.1"` - Full version number `M.N.U`
    - `MN="0.10"` or `MN="0.9"` - Major and minor version number `M.N`
    - `BRANCH="master"` or `BRANCH="stable_$MN"`

3.  Check out the branch the new version is based upon, make sure it is up to
    date with upstream, and create a topic branch for the new version:

    - `git checkout $BRANCH`
    - `git pull`
    - `git checkout -b start_$MNU`

4.  Edit the version file and set the version to the new development version:

    - `vi pywbem/_version.py`

    `__version__ = 'M.N.U.dev1'`

    Where `M.N.U` is the new version to be started, e.g. `0.10.0`.

5.  Edit the change log:

    - `vi docs/changes.rst`

    To insert the following section before the top-most section:

    ```
    pywbem 0.10.0.dev1
    ------------------

    This version is currently in development and is shown as |version|.

    This version contains all fixes up to pywbem 0.9.x.

    Released: not yet

    **Incompatible changes:**

    **Deprecations:**

    **Bug fixes:**

    **Enhancements:**

    **Known issues:**

    * See `list of open issues`_.

    .. _`list of open issues`: https://github.com/pywbem/pywbem/issues
    ```

6. Commit the changes and push to upstream:

    - `git status` - to double check which files have been changed
    - `git commit -asm "Start $MNU"`
    - `git push --set-upstream origin start_$MNU`

7.  On Github, create a Pull Request for branch `start_$MNU`.

    Important: When creating Pull Requests, GitHub by default targets
    the `master` branch. If you are starting a fix version, you need to
    change the target branch of the Pull Request to `stable_M.N`.

8.  On GitHub, once all of these tests succeed:

    - Merge the Pull Request (no review is needed)
    - Delete the branch of the Pull Request (`release_M.N.U`)

9.  Checkout the branch the new version is based upon, update it from
    upstream, and delete the local topic branch you created:

    - `git checkout $BRANCH`
    - `git pull`
    - `git branch -d start_$MNU`

10. On GitHub, create a new milestone `M.N.U` for the version that is started.

11. On GitHub, list all open issues that still have a milestone of less than
    `M.N.U` set, and update them as needed to target milestone `M.N.U`.
