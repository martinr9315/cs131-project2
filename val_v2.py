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
  def __init__(self, type, value=None):
    self.t = type
    self.v = value

  def value(self):
    return self.v

  def set(self, other):
    self.t = other.t
    self.v = other.v

  def type(self):
    return self.t
  
  def __str__(self):
    return ("{type:" +str(self.t)+" value:"+str(self.v)+"}")