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
  - Make sure the correct long-lived branch is used as a merge target!
  - Review happens as comments on the pull requests.
  - At least two +1 are required for merging.

Releasing to PyPI
-----------------

Currently, there is quite a bit of manual work to be done for a release to
PyPI. This is all done by one person, and it assumes that the `pywbem/pywbem`
repo and the `pywbem/pywbem.github.io` repo are both cloned locally in
adjacent directories named `pywbem` and `pywbem.github.io`.
The upstream repos are assumed to have the remote name `origin`.

In the following description, `M.N.U` stands for the version that is to be
released.

In the directory of the `pywbem` repo:

1.  Make sure the branch is checked out that is to be released, and that it
    is in a git-wise clean state:
    - `git status` - to verify checked out branch and clean state
    - `git log` - to verify the content of this branch
2.  Create a topic branch:
    - `git checkout -b release_M.N.U`
3.  Finalize package versions (i.e. change development version `M.N.U.dev0` to
    final version `M.N.U`):
    - `vi setup.py`
    - `vi pywbem/__init__.py`
    - `vi pywbem/NEWS.md`
4.  Make sure the change log reflects all changes in the release:
    - `vi pywbem/NEWS.md`
5.  Perform a complete build (in a Python virtual environment):
    - `make clobber all`
6.  If this fails, fix and iterate back to step 5 until it succeeds.
7.  Create README file in distribution directory:
    - Only if the `dist/pywbem-M.N/README.md` file does not yet exist:
      - `find dist -name README.md | sort | tail | xargs cp -t dist/pywbem-M.N/`
      - `vi dist/pywbem-M.N/README.md` - adjust to this release
8.  Commit and push to upstream repo:
    - `git commit -m "Release vM.N.U"`
    - `git push --set-upstream origin release_M.N.U` - if branch is pushed for the first time
    - `git push` - after first time, for normal additional commit
    - `git push -f` - after first time, if a rebase was used
9.  On Github, create a Pull Request for the target branch. This will trigger
    the Travis CI run. **Important:** Regardless of which branch the commit was
    based upon, Github will by default target the master branch for the merge.
    So if your base branch for this release was not `master`, change the target
    branch for the PR to be your base branch.
10. Perform a complete test:
    - `tox`
11. Perform an install test:
    - `cd testsuite; ./test_install.sh`
12. Perform any other tests you wish, e.g.
    - Run in local CI environment
    - Run against a real WBEM server
13. If any of the tests (including the Travis CI run of the Pull Request) fails,
    fix and iterate back to (1) until they all succeed.
14. Once the Travis CI run for this PR succeeds:
    - Merge the PR (no review is needed)
    - Delete the PR
15. Clean up local branches:
    - `git-prune origin` (From `andy-maier/gitsurvival`)
16. Close milestone `M.N.U` on GitHub.
    Tag the release and push to upstream repo:
    - Create tag for M.N.U:
      - `git tag vM.N.U`
    - Delete preliminary M.N* tags, if any:
      - `git tag | grep "M.N"`
      - `git tag -d <tags ...>`
    - Push tag changes:
      - `git push --tags`
17. On GitHub, edit the new tag, and create a release description on it. This
    will cause it to appear in the Release tab.
18. Upload the package to PyPI:
    - **Attention!!** This only works once. You cannot re-release the same
      version to PyPI.
    - `make release`
    - Verify that it arrived on PyPI:
      - https://pypi.python.org/pypi/pywbem/M.N.U
19. Publish the API docs to the adjacent `pywbem.github.io` repo directory:
    - `make publish`

In the directory of the `pywbem.github.io` repo:
 
1.  Make sure the `master` branch is checked out, and that it is in a git-wise
    clean state:
    - `git status`
2.  Copy and adjust HTML files for API docs of new release by finalizing version:
    - `cp pywbem/doc/latest/*.html pywbem/doc/M.N.U/`
    - `vi pywbem/doc/M.N.U/index.html`
    - `vi pywbem/doc/M.N.U/changelog.html`
3. Update download table in `pywbem/installation.html` for new release:
    - `vi pywbem/installation.html`
4.  If `M.N.U` is higher than any other released version, adjust the *latest
    release* link:
    - `rm pywbem/doc/latest`
    - `ln -s M.N.U pywbem/doc/latest`
5.  Verify that the installation page (`pywbem/installation.html` in your web
    browser) shows the new release correctly, and that all of its links work.
6.  Commit in master branch and push to upstream repo:
    - `git commit -m "Release vM.N.U"`
    - `git push` - for normal additional commit
    - `git push -f` - if a rebase was used
7.  Verify that the installation page of `http://pywbem.github.io/pywbem` is
    updated, and that all the links work and show the intended version.

Announcement on `pywbem-devel` mailing list.

Starting development of a new release
-------------------------------------

For the functional release/branch, this can be done right after releasing it.
For a fix release/branch, one can wait until it is needed.

In the following description, `M.N.U` stands for the new version whose
development is to be started.

In the directory of the `pywbem` repo:

1.  Make sure the desired functional or fix branch that is to be used
    as the basis for the new development, is checked out, and that it
    is in a git-wise clean state:
    - `git status` - to verify checked out branch and clean state
2.  Create README file in distribution directory:
    - Only if the `dist/pywbem-M.N/README.md` file does not yet exist:
      - `find dist -name README.md | sort | tail | xargs cp -t dist/pywbem-M.N/`
      - `vi dist/pywbem-M.N/README.md` - adjust to this release
3.  Create a topic branch:
    - `git checkout -b start_M.N.U`
4.  Bump package versions up and add development suffix (i.e. change to version
    `M.N.U.dev0`):
    - `vi setup.py`
    - `vi pywbem/__init__.py`
    - `vi pywbem/NEWS.md` - Add a new section for the new release, at the
      by date, so it is possible that a new fix version v0.8.2.dev0 that gets
      added is followed by v0.9.0 which is followed by v0.8.1, if v0.9.0 was
      already released at the time v0.8.2 is started.
5.  Commit and push to upstream repo:
    - `git commit -m "Start development of vM.N.U"`
    - `git push --set-upstream origin release_M.N.U` - if branch is pushed for
      the first time
    - `git push` - after first time, for normal additional commit
    - `git push -f` - after first time, if a rebase was used
6.  On Github, create a Pull Request for the target branch. This will trigger
    the Travis CI run. **Important:** Regardless of which branch the commit was
    based upon, Github will by default target the master branch for the merge.
    So if your base branch for this release was not `master`, change the target
    branch for the PR to be your base branch.
7.  If the Travis CI run fails, fix and iterate back to step 5. until they all
    succeed.
8.  Once the Travis CI run for this PR succeeds:
    - Merge the PR (no review is needed)
    - Delete the PR
9.  Create milestone `M.N.U` on GitHub.
10. Clean up local branches:
    - `git-prune origin` (From `andy-maier/gitsurvival`)

