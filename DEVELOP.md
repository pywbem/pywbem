Releasing PyWBEM
================

Git workflow
------------

* Long-lived branches:
  - ``master`` - for next functional version
  - ``stable_M.N`` - for fix stream of released version M.N.
* We use topic branches for everything!
  - Based upon the intended long-lived branch, if no dependencies
  - Based upon an earlier topic branch, in case of dependencies
  - It is valid to rebase topic branches and force-push them.
* We use pull requests to review the branches.
  - Use the correct long-lived branch (e.g. ``master`` or ``stable_0.8``) as a
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

It covers all variants of versions that can be released:

* Releasing a new major version (Mnew.0.0) based on the master branch
* Releasing a new minor version (M.Nnew.0) based on the master branch
* Releasing a new update version (M.N.Unew) based on the stable branch of its
  minor version

The description assumes that the ``pywbem/pywbem`` repo is cloned locally, and
its upstream repo is assumed to have the remote name ``origin``.

Any commands in the following steps are executed in the main directory of your
local clone of the ``pywbem/pywbem`` Git repo.

1.  Set shell variables for the version that is being released and the branch
    it is based on:

    * ``MNU`` - Full version M.N.U that is being released
    * ``MN`` - Major and minor version M.N of that full version
    * ``BRANCH`` - Name of the branch the version that is being released is
      based on

    When releasing a new major version (e.g. ``1.0.0``) based on the master
    branch:

        MNU=1.0.0
        MN=1.0
        BRANCH=master

    When releasing a new minor version (e.g. ``0.9.0``) based on the master
    branch:

        MNU=0.9.0
        MN=0.9
        BRANCH=master

    When releasing a new update version (e.g. ``0.8.1``) based on the stable
    branch of its minor version:

        MNU=0.8.1
        MN=0.8
        BRANCH=stable_${MN}

2.  Create a topic branch for the version that is being released:

        git checkout ${BRANCH}
        git pull
        git checkout -b release_${MNU}

3.  Edit the change log:

        vi docs/changes.rst

    and make the following changes in the section of the version that is being
    released:

    * Finalize the version.
    * Change the release date to today's date.
    * Make sure that all changes are described.
    * Make sure the items shown in the change log are relevant for and
      understandable by users.
    * In the "Known issues" list item, remove the link to the issue tracker and
      add text for any known issues you want users to know about.
    * Remove all empty list items.

4.  Edit the README file for PyPI:

        vi README_PYPI.md

    and update the constants near the top of the file:

        .. |pywbem-version-mn| replace:: M.N
        .. _Readme file on GitHub: https://github.com/pywbem/pywbem/blob/stable_M.N/README.md
        .. _Documentation on RTD: https://pywbem.readthedocs.io/en/stable_M.N/
        .. _Change log on RTD: https://pywbem.readthedocs.io/en/stable_M.N/changes.html

5.  Run the Safety tool:

    .. code-block:: sh

        RUN_TYPE=release make safety

    When releasing a version, the safety run for all dependencies will fail
    if there are any safety issues reported. In normal and scheduled runs,
    safety issues reported for all dependencies will be ignored.

    If the safety run fails, you need to fix the safety issues that are
    reported.

6.  Commit your changes and push the topic branch to the remote repo:

        git commit -asm "Release ${MNU}"
        git push --set-upstream origin release_${MNU}

7.  On GitHub, create a Pull Request for branch ``release_M.N.U``. This will
    trigger the CI runs.

    Important: When creating Pull Requests, GitHub by default targets the
    ``master`` branch. When releasing based on a stable branch, you need to
    change the target branch of the Pull Request to ``stable_M.N``.

    Set the milestone of that PR to version M.N.U.

    The PR creation will cause the "test" workflow to run. That workflow runs
    tests for all defined environments, since it discovers by the branch name
    that this is a PR for a release.

8.  On GitHub, close milestone ``M.N.U``.

    Verify that the milestone has no open items anymore. If it does have open
    items, investigate why and fix.

9.  On GitHub, once the checks for the Pull Request for branch ``release_M.N.U``
    have succeeded, merge the Pull Request (no review is needed). This
    automatically deletes the branch on GitHub.

    If the PR did not succeed, fix the issues.

10. Publish the package

        git checkout ${BRANCH}
        git pull
        git branch -D release_${MNU}
        git branch -D -r origin/release_${MNU}
        git tag -f ${MNU}
        git push -f --tags

    Pushing the new tag will cause the "publish" workflow to run. That workflow
    builds the package, publishes it on PyPI, creates a release for it on Github,
    and finally creates a new stable branch on Github if the master branch was
    released.

11. Verify the publishing

    Wait for the "publish" workflow for the new release to have completed:
    https://github.com/pywbem/pywbem/actions/workflows/publish.yml

    Then, perform the following verifications:

    * Verify that the new version is available on PyPI at
      https://pypi.python.org/pypi/pywbem/

    * Verify that the new version has a release on Github at
      https://github.com/pywbem/pywbem/releases

    * Verify that the new version has documentation on ReadTheDocs at
      https://pywbem.readthedocs.io/en/stable/changes.html

      The new version M.N.U should be automatically active on ReadTheDocs,
      causing the documentation for the new version to be automatically built
      and published.

      If you cannot see the new version after some minutes, log in to
      https://readthedocs.org/projects/pywbem/versions/ and activate
      the new version.


Starting a new version
----------------------

This section shows the steps for starting development of a new version of pywbem.

This section covers all variants of new versions:

* Starting a new major version (Mnew.0.0) based on the master branch
* Starting a new minor version (M.Nnew.0) based on the master branch
* Starting a new update version (M.N.Unew) based on the stable branch of its
  minor version

The description assumes that the ``pywbem/pywbem`` repo is cloned locally in a
directory named ``pywbem``. Its upstream repo is assumed to have the remote name
``origin``.

Any commands in the following steps are executed in the main directory of your
local clone of the ``pywbem/pywbem`` Git repo.

1.  Set shell variables for the version that is being started and the branch it
    is based on:

    * ``MNU`` - Full version M.N.U that is being started
    * ``MN`` - Major and minor version M.N of that full version
    * ``BRANCH`` -  Name of the branch the version that is being started is
      based on

    When starting a new major version (e.g. ``1.0.0``) based on the master
    branch:

        MNU=1.0.0
        MN=1.0
        BRANCH=master

    When starting a new minor version (e.g. ``0.9.0``) based on the master
    branch:

        MNU=0.9.0
        MN=0.9
        BRANCH=master

    When starting a new minor version (e.g. ``0.8.1``) based on the stable
    branch of its minor version:

        MNU=0.8.1
        MN=0.8
        BRANCH=stable_${MN}

2.  Create a topic branch for the version that is being started:

        git checkout ${BRANCH}
        git pull
        git checkout -b start_${MNU}

3.  Edit the change log:

        vi docs/changes.rst

    and insert the following section before the top-most section:

        pywbem M.N.U.dev
        ----------------

        This version contains all fixes up to version M.N-1.x.

        Released: not yet

        **Incompatible changes:**

        **Deprecations:**

        **Bug fixes:**

        **Enhancements:**

        **Cleanup:**

        **Known issues:**

        * See `list of open issues`_.

        .. _`list of open issues`: https://github.com/pywbem/pywbem/issues

4.  Add an initial Git tag for the new release stream and push it to the
    remote repo.

    Note: An initial tag is necessary because the automatic version calculation
    done by setuptools-scm uses the most recent tag in the commit history and
    increases the least significant part of the version by one, without
    providing any controls to change that behavior. So without this initial tag
    when developing 1.8.0, the most recent tag would be 1.7.0 and the calculated
    version would be e.g. 1.7.1.dev11+g7c3eb911. The "a0" at the end of the tag
    is necessary because it adds a new least significant part, so the rest of
    the version is not increased. So when developing 1.8.0, the calculated
    version is e.g. 1.8.0a1.dev11+g7c3eb911.

    Note that the "publish" workflow will not run for this tag.

        git tag ${MNU}a0
        git push --tags

5.  Commit your changes and push them to the remote repo:

        git commit -asm "Start ${MNU}"
        git push --set-upstream origin start_${MNU}

6.  On GitHub, create a Pull Request for branch ``start_M.N.U``.

    Important: When creating Pull Requests, GitHub by default targets the
    ``master`` branch. When starting a version based on a stable branch, you
    need to change the target branch of the Pull Request to ``stable_M.N``.

7.  On GitHub, create a milestone for the new version ``M.N.U``.

    You can create a milestone in GitHub via Issues -> Milestones -> New
    Milestone.

8.  On GitHub, go through all open issues and pull requests that still have
    milestones for previous releases set, and either set them to the new
    milestone, or to have no milestone.

9.  On GitHub, once the checks for the Pull Request for branch ``start_M.N.U``
    have succeeded, merge the Pull Request (no review is needed). This
    automatically deletes the branch on GitHub.

10. Update and clean up the local repo:

        git checkout ${BRANCH}
        git pull
        git branch -D start_${MNU}
        git branch -D -r origin/start_${MNU}
