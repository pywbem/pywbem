from __future__ import absolute_import, print_function
import os
from .utils import import_installed
pywbem = import_installed('pywbem')

print("Testing pywbem version {0} from {1}".
      format(pywbem.__version__, os.path.dirname(pywbem.__file__)))
