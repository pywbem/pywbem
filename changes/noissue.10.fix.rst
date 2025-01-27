Development: Removed 'upload' target from Makefile, and dependency to 'twine'
package and some of its dependent packages. It is no longer needed since the
introduction of the publish.yml GitHub Actions workflow.
