# -*- coding: iso-8859-1 -*-
ur"""Each process has an environment block (which may be empty). It
consists of a set of key-value pairs, each of which is a string.
The value string may be formed partly or wholly from other environment
variables using the %envvar% notation. By default, this module will
reinterpret those embedded variables but this can be overriden.

The process environment is derived on startup from a combination
of the system environment variables and the user's environment
variable, some of which are generated automatically by the
system to reflect the user's profile location and home drive etc.

All three environments are available as a dictalike class whose
interface matches the :class:`Env` base class. Each environment
object quacks like a dict in respect of item access, :meth:`Env.get`,
:meth:`Env.keys`, :meth:`Env.items` and :meth:`Env.update` methods 
and the system and user objects supply an additional :meth:`Persistent.broadcast` 
method which sends a message to top-level windows, such as the shell, to 
indicate that the environment has changed.
"""
import win32api
import win32profile
import win32gui
import win32con
import winerror

from winsys import core, exc, utils, registry

class x_environment (exc.x_winsys):
  "Base exception for all env exceptions"

WINERROR_MAP = {
  winerror.ERROR_ENVVAR_NOT_FOUND : exc.x_not_found,
}
wrapped = exc.wrapper (WINERROR_MAP, x_environment)

class Env (core._WinSysObject):
  ur"""Semi-abstract base class for all environment classes. Outlines
  a dict-like interface which relies on subclasses to implement simple
  :meth:`_get` and :meth:`_items` methods.
  """  
  def __getitem__ (self, item):
    ur"""Get environment strings like dictionary items::
    
      from winsys import environment
      
      print environment.system ()['windir']
    """
    raise NotImplementedError
  
  def __setitem__ (self, item, value):
    ur"""Set environment strings like dictionary items::
    
      from winsys import environment
      
      environment.user ()['winsys'] = 'TEST'
    """
    raise NotImplementedError
    
  def __delitem__ (self, item, value):
    ur"""Remove an item from the environment::
    
      from winsys import environment
      
      del environment.process ()['winsys']
    """
    raise NotImplementedError
  
  def __repr__ (self):
    return repr (dict (self.items ()))
    
  def dumped (self, level):
    return utils.dumped_dict (dict (self.items ()), level)

  def keys (self):
    """Yield environment variable names
    """
    raise NotImplementedError
  
  def items (self, expand=True):
    """Yield key-value pairs of environment variables
    
    :param expand: whether to expand embedded environment variables [True]
    """
    return (  
      (k, self.expand (v) if expand else v) 
        for k, v 
        in self._items ()
    )
    
  def get (self, item, default=None, expand=True):
    """Return an environment value if it exists, otherwise
    `[default]`. This is the only way to get an unexpanded
    environment value by setting `expand` to False.
    
    :param item: name of an environment variable
    :param default: value to return if no such environment variable exists.
                    This default is expanded if `expand` is True.
    :param expand: whether to expand embedded environment variables [True]
    """
    try:
      v = self._get (item)
    except KeyError:
      return default
    else:
      return self.expand (v) if expand else v
  
  def update (self, dict_initialiser):
    """Update this environment from a dict-like object, typically
    another environment::
    
      from winsys import environment
      
      penv = environment.process ()
      penv.update (environment.system ())
    """
    for k, v in dict (dict_initialiser).items ():
      self[k] = v
      
  @staticmethod
  def expand (item):
    """Return a version of `item` with internal environment variables
    expanded to their corresponding value. This is done automatically
    by the functions in this class unless you specify `expand=False`.
    """
    return wrapped (win32api.ExpandEnvironmentStrings, unicode (item))
  
class Process (Env):
  def __init__ (self):
    super (Process, self).__init__ ()
    
  def keys (self):
    return (k for k in wrapped (win32profile.GetEnvironmentStrings).keys ())
  
  def _items (self):
    return (item for item in wrapped (win32profile.GetEnvironmentStrings).items ())
  
  def _get (self, item):
    return wrapped (win32api.GetEnvironmentVariable, item)
  
  def __getitem__ (self, item):
    value = self._get (item)
    if value is None:
      raise KeyError
    else:
      return unicode (value)
    
  def __setitem__ (self, item, value):
    if value is None:
      wrapped (win32api.SetEnvironmentVariable, item, None)
    else:
      wrapped (win32api.SetEnvironmentVariable, item, unicode (value))
  
  def __delitem__ (self, item):
    wrapped (win32api.SetEnvironmentVariable, item, None)
    
class Persistent (Env):
  ur"""Represent persistent (registry-based) environment variables. These
  are held at system and at user level, the latter overriding the former
  when an process environment is put together. Don't instantiate this
  class directly: use the :func:`user` and :func:`system` functions.
  """
  
  @staticmethod
  def broadcast ():
    ur"""Broadcast a message to all top-level windows informing them that
    an environment change has occurred. The message must be sent, not posted,
    and times out after two seconds since some top-level windows handle this
    badly.
    """
    win32gui.SendMessageTimeout (
      win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 
      0, "Environment", 
      win32con.SMTO_ABORTIFHUNG, 2000
    )

  def __init__ (self, root):
    super (Persistent, self).__init__ ()
    self.registry = registry.registry (root)
    
  def _get (self, item):
    try:
      return unicode (self.registry.get_value (item))
    except exc.x_not_found:
      return None
  
  def keys (self):
    return (name for name, value in self.registry.values ())
  
  def _items (self):
    return self.registry.values ()
  
  def __getitem__ (self, item):
    value = self._get (item)
    if value is None:
      raise KeyError
    else:
      return value
    
  def __setitem__ (self, item, value):
    self.registry.set_value (item, unicode (value))
    
  def __delitem__ (self, item):
    del self.registry[item]
    
def process ():
  ur"""Return a dict-like object representing the environment block of the
  current process.
  """
  return Process ()

def system (machine=None):
  ur"""Return a dict-like object representing the system-level persistent
  environment variables, optionally selecting a different machine.
  
  :param machine: name or address of a different machine whose system
                  environment is to be represented.
  """
  ROOT = r"HKLM\System\CurrentControlSet\Control\Session Manager\Environment"
  if machine:
    root = r"\\%s\%s" % (machine, ROOT)
  else:
    root = ROOT
  return Persistent (root)

def user ():
  ur"""Return a dict-like object representing the user-level persistent
  environment for the logged-on user.
  
  TODO: include alternate user functionality via logon token
  """
  return Persistent (ur"HKCU\Environment")
