import os, sys
import operator

from nose.tools import *

from winsys import _aces, _acls, accounts
import win32api
import win32con
import win32security
import ntsecuritycon
import tempfile

everyone, _, _ = win32security.LookupAccountName (None, "Everyone")
me, _, _ = win32security.LookupAccountName (None, win32api.GetUserNameEx (win32con.NameSamCompatible))

def test_acl_None ():
  acl = _acls.acl (None)
  assert isinstance (acl, _acls.ACL) and acl.pyobject () is None

def test_acl_PyACL ():
  dacl = win32security.ACL ()
  dacl.AddAccessAllowedAceEx (win32security.ACL_REVISION_DS, 0, ntsecuritycon.FILE_READ_DATA, everyone)
  acl = _acls.acl (dacl).pyobject ()
  assert dacl.GetAceCount () == 1
  assert dacl.GetAce (0) == ((win32security.ACCESS_ALLOWED_ACE_TYPE, 0), ntsecuritycon.FILE_READ_DATA, everyone)

def test_acl_ACL ():
  acl0 = _acls.ACL ()
  acl = _acls.acl (acl0)
  assert acl is acl0

def test_acl_iterable ():
  aces0 = [("Everyone", "R", "Allow"), ("Administrators", "F", "Allow")]
  def iteraces ():
    for ace in aces0:
      yield ace
  assert list (_acls.acl (iteraces ())) == list (_aces.ace (ace) for ace in aces0)

def test_ACL_iterated ():
  #
  # This includes a test for sorting, putting deny records first
  #
  acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
  assert list (acl) == [
    _aces.ace (("Administrators", "F", "Deny")), 
    _aces.ace (("Everyone", "R", "Allow"))
  ]

def test_ACL_append ():
  acl = _acls.acl ([("Everyone", "R", "Allow")])
  acl.append (("Administrators", "F", "Deny"))
  assert list (acl) == [
    _aces.ace (("Administrators", "F", "Deny")), 
    _aces.ace (("Everyone", "R", "Allow"))
  ]

def test_ACL_getitem ():
  acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
  #
  # Note that the list is *stored* in the order entered; it
  # is only returned (via pyobject) in sorted order.
  #
  assert acl[0] == ("Everyone", "R", "Allow")

def test_ACL_setitem ():
  acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
  acl[0] = ((me, "R", "Allow"))
  assert acl[0] == (me, "R", "Allow")

def test_ACL_delitem ():
  acl = _acls.acl ([("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")])
  del acl[0]
  assert list (acl) == [
    _aces.ace (("Administrators", "F", "Deny")), 
  ]

def test_ACL_len ():
  aces = [("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")]
  acl = _acls.acl (aces)
  assert len (acl) == len (aces)

def test_ACL_nonzero ():
  assert not _acls.acl (None)
  assert not _acls.acl ([])
  assert _acls.acl ([("Everyone", "R", "Allow")])

def test_ACL_contains ():
  aces = [("Everyone", "R", "Allow"), ("Administrators", "F", "Deny")]
  acl = _acls.acl (aces)
  for ace in aces:
    assert ace in acl
  assert ("Everyone", "F", "Deny") not in acl

def test_ACL_public ():
  acl = _acls.ACL.public ()
  assert list (acl) == [("Everyone", "F", "ALLOW")]

def test_ACL_private ():
  acl = _acls.ACL.private ()
  assert list (acl) == [(me, "F", "ALLOW")]