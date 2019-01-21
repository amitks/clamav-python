## TODO: boilerplate ##


from distutils.command.build import build
from distutils.command.build_ext import build_ext
from setuptools import setup, Command, Extension, find_packages
from codecs import open

import distutils.errors
import distutils.ccompiler
import distutils.sysconfig

import contextlib
import os
import sys
import tempfile
import shutil
import subprocess


OPTIONS = [
   ('dynamic-linking', None, 'link dynamically against libclamav'),
   ('enable-debug', None, 'enable debug logs')]


BOOLEAN_OPTIONS = [
    'dynamic-linking',
    'enable-debug']


@contextlib.contextmanager
def muted(*streams):
  """A context manager to redirect stdout and/or stderr to /dev/null.

  Examples:
    with muted(sys.stdout):
      ...

    with muted(sys.stderr):
      ...

    with muted(sys.stdout, sys.stderr):
      ...
  """
  devnull = open(os.devnull, 'w')
  try:
    old_streams = [os.dup(s.fileno()) for s in streams]
    for s in streams:
      os.dup2(devnull.fileno(), s.fileno())
    yield
  finally:
    for o,n in zip(old_streams, streams):
      os.dup2(o, n.fileno())
    devnull.close()


def has_function(function_name, libraries=None):
  """Checks if a given functions exists in the current platform."""
  compiler = distutils.ccompiler.new_compiler()
  with muted(sys.stdout, sys.stderr):
    result = compiler.has_function(
        function_name, libraries=libraries)
  if os.path.exists('a.out'):
    os.remove('a.out')
  return result


class BuildCommand(build):

  user_options = build.user_options + OPTIONS
  boolean_options = build.boolean_options + BOOLEAN_OPTIONS

  def initialize_options(self):

    build.initialize_options(self)
    self.dynamic_linking = None
    self.enable_debug = None

  def finalize_options(self):

    build.finalize_options(self)



class BuildExtCommand(build_ext):

  user_options = build_ext.user_options + OPTIONS
  boolean_options = build_ext.boolean_options + BOOLEAN_OPTIONS

  def initialize_options(self):

    build_ext.initialize_options(self)
    self.dynamic_linking = None
    self.enable_debug = None

  def finalize_options(self):

    build_ext.finalize_options(self)

    # If the build_ext command was invoked by the build command, take the
    # values for these options from the build command.

    self.set_undefined_options('build',
        ('dynamic_linking', 'dynamic_linking'),
        ('enable_debug', 'enable_debug'))

  def run(self):
    """Execute the build command."""

    module = self.distribution.ext_modules[0]
    base_dir = os.path.dirname(__file__)

    if base_dir:
      os.chdir(base_dir)

    exclusions = []

    for define in self.define or []:
      module.define_macros.append(define)

    for library in self.libraries or []:
      module.libraries.append(library)

    building_for_windows = self.plat_name in ('win32','win-amd64')
    building_for_osx = 'macosx' in self.plat_name
    building_for_linux = 'linux' in self.plat_name
    building_for_freebsd = 'freebsd' in self.plat_name
    building_for_openbsd = 'openbsd' in self.plat_name # need testing

    if building_for_linux:
      module.define_macros.append(('USE_LINUX_PROC', '1'))
    elif building_for_windows:
      module.define_macros.append(('USE_WINDOWS_PROC', '1'))
      module.define_macros.append(('_CRT_SECURE_NO_WARNINGS', '1'))
      module.libraries.append('kernel32')
      module.libraries.append('advapi32')
      module.libraries.append('user32')
      module.libraries.append('crypt32')
      module.libraries.append('ws2_32')
    elif building_for_osx:
      module.define_macros.append(('USE_MACH_PROC', '1'))
      module.include_dirs.append('/usr/local/opt/openssl/include')
      module.include_dirs.append('/opt/local/include')
      module.library_dirs.append('/opt/local/lib')
      module.include_dirs.append('/usr/local/include')
      module.library_dirs.append('/usr/local/lib')
    elif building_for_freebsd:
      module.define_macros.append(('USE_FREEBSD_PROC', '1'))
      module.include_dirs.append('/opt/local/include')
      module.library_dirs.append('/opt/local/lib')
      module.include_dirs.append('/usr/local/include')
      module.library_dirs.append('/usr/local/lib')
    elif building_for_openbsd:
      module.define_macros.append(('USE_OPENBSD_PROC', '1'))
      module.include_dirs.append('/opt/local/include')
      module.library_dirs.append('/opt/local/lib')
      module.include_dirs.append('/usr/local/include')
      module.library_dirs.append('/usr/local/lib')
    else:
      module.define_macros.append(('USE_NO_PROC', '1'))

    if has_function('memmem'):
      module.define_macros.append(('HAVE_MEMMEM', '1'))
    if has_function('strlcpy'):
      module.define_macros.append(('HAVE_STRLCPY', '1'))
    if has_function('strlcat'):
      module.define_macros.append(('HAVE_STRLCAT', '1'))

    if self.dynamic_linking:
      module.libraries.append('clamav')
    else:
      pass
      ## TODO: add static linking logic.

    if self.enable_debug:
      module.define_macros.append(('DEBUG', '1'))
    else:
      pass

    ## as of now default is dynamic linking.
    module.libraries.append('clamav')
    build_ext.run(self)


class UpdateCommand(Command):
  """Update libclamav source.

  This is normally only run by packagers to make a new release.
  """
  user_options = []

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    pass
    ## TODO: add clamav src update logic here.


with open('README.md', 'r', 'utf-8') as f:
  readme = f.read()

setup(
    name='clamav-python',
    version='1.0.0',
    description='Python interface for CLAMAV',
    long_description=readme,
    license='Apache 2.0',
    author='Amit Kumar',
    author_email='msnamit@gmail.com',
    url='https://github.com/amitks/clamav-python.git',
    zip_safe=False,
    cmdclass={
        'build': BuildCommand,
        'build_ext': BuildExtCommand,
        'update': UpdateCommand},
    ext_modules=[Extension(
        name='clamav',
        sources=['clamav-python.c'])])
