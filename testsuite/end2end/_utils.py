"""
Utility functions for end2end tests.
"""

from __future__ import absolute_import, print_function


def _latest_profile_inst(profile_insts):
    """
    Determine the instance with the latest version in a list of registered
    profile instances and return that instance.
    """
    profile_versions = [inst['RegisteredVersion'] for inst in profile_insts]
    latest_i = None
    latest_version = [0, 0, 0]
    for i, profile_version in enumerate(profile_versions):
        profile_version = [int(v) for v in profile_version.split('.')]
        if profile_version > latest_version:
            latest_version = profile_version
            latest_i = i
    latest_profile_inst = profile_insts[latest_i]
    return latest_profile_inst
