#!/usr/bin/env python
# Environment.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 18th September 2006
#
# A handler for matters of the operating environment, which will impact
# on data harvesting, working directories, a couple of other odds & sods.

import os
import sys
import subprocess
import stat
import platform
import ctypes
import tempfile

from xia2.Handlers.Streams import Chatter, Debug

def memory_usage():
  try:
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
  except:
    return 0

def debug_memory_usage():
  '''Print line, file, memory usage.'''

  import exceptions

  try:
    import inspect

    frameinfo = inspect.getframeinfo(inspect.stack()[1][0])
    Debug.write('RAM usage at %s %d: %d' %
                (os.path.split(frameinfo.filename)[-1], frameinfo.lineno,
                 memory_usage()))
  except exceptions.Exception, e:
    Debug.write('Error getting RAM usage: %s' % str(e))
  return

def df(path = os.getcwd()):
  '''Return disk space in bytes in path.'''

  if platform.system() == 'Windows':
    bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(path), None, None, ctypes.pointer(bytes))
    return bytes.value
  else:
    s = os.statvfs(path)
    return s.f_frsize * s.f_bavail

  raise RuntimeError, 'platform not supported'

class _Environment(object):
  '''A class to store environmental considerations.'''

  def __init__(self):
    self._cwd = os.getcwd()
    self._is_setup = False
    return

  def _setup(self):
    if self._is_setup:
      return

    # Make sure USER env var is defined (historical reasons)

    if not 'USER' in os.environ:
      if 'USERNAME' in os.environ:
        os.environ['USER'] = os.environ['USERNAME']
      else:
        os.environ['USER'] = 'xia2'

    # define a local CCP4_SCR

    ccp4_scr = tempfile.mkdtemp()
    os.environ['CCP4_SCR'] = ccp4_scr
    Debug.write('Created CCP4_SCR: %s' % ccp4_scr)

    self._is_setup = True

    return

  def generate_directory(self, path_tuple):
    '''Used for generating working directories.'''
    self._setup()

    path = self._cwd

    if type(path_tuple) == type('string'):
      path_tuple = (path_tuple,)

    for p in path_tuple:
      path = os.path.join(path, p)

    if not os.path.exists(path):
      Debug.write('Making directory: %s' % path)
      os.makedirs(path)
    else:
      Debug.write('Directory exists: %s' % path)

    return path

  def setenv(self, name, value):
    '''A wrapper for os.environ.'''

    self._setup()
    os.environ[name] = value

    return

  def getenv(self, name):
    '''A wrapper for os.environ.'''
    self._setup()
    return os.environ.get(name, None)

  def cleanup(self):
    return

Environment = _Environment()

# jiffy functions

def get_number_cpus():
  '''Portably get the number of processor cores available.'''
  from libtbx.introspection import number_of_processors
  return number_of_processors(return_value_if_unknown=-1)

if __name__ == '__main__':

  print get_number_cpus()
  print df(os.getcwd())
