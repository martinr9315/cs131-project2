from enum import Enum
class Type(Enum):
  INT = 1
  BOOL = 2
  STRING = 3
  REFINT = 4
  REFBOOL = 5
  REFSTRING = 6

# Represents a value, which has a type and its value
class Value:
  def __init__(self, type, value=None, ref=None):
    self.t = type
    self.v = value
    self.r = ref

  def value(self):
    return self.v
  
  def update_only_val(self, value):
    self.v = value
    return self

  def set(self, other):
    self.t = other.t
    self.v = other.v
    self.r = other.r

  def set_ref(self, ref_var):
    self.r = ref_var
  
  def ref(self):
    return self.r

  def ref_var(self):
    return self.r[0]
  
  def ref_info(self):
    return self.r[1]

  def type(self):
    return self.t
  
  def __str__(self):
    return ("(type:" +str(self.t)+", value:"+str(self.v)+", ref:"+str(self.r)+")")