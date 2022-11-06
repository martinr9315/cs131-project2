from intbase import InterpreterBase
from val_v2 import Value, Type

# FuncInfo is a class that represents information about a function
# Right now, the only thing this tracks is the line number of the first executable instruction
# of the function (i.e., the line after the function prototype: func foo)
class FuncInfo:
  def __init__(self, start_ip, inputs, return_var=None):
    self.start_ip = start_ip    # line number, zero-based
    self.inputs = inputs        # list of tuples of variable names and Value objects
    self.return_var = return_var
  
  def __str__(self):
    s = "inputs: "+self.inputs.__str__()+" return:"+self.return_var.__str__()
    return s

# FunctionManager keeps track of every function in the program, mapping the function name
# to a FuncInfo object (which has the starting line number/instruction pointer) of that function.
class FunctionManager:
  def __init__(self, tokenized_program):
    self.func_cache = {}
    self._cache_function_line_numbers(tokenized_program)

  def get_function_info(self, func_name):
    if func_name not in self.func_cache:
      return None
    return self.func_cache[func_name]

  def _cache_function_line_numbers(self, tokenized_program):
    for line_num, line in enumerate(tokenized_program):
      if line and line[0] == InterpreterBase.FUNC_DEF:
        func_name = line[1]
        input_values = [(name,self._get_value_type(val)) for name, val in [input.split(":") for input in line[2:-1]]]
        # TODO: edge case - error if multiple same var used as input?
        return_type = self._get_value_type(line[-1])
        func_info = FuncInfo(line_num + 1, input_values, return_type)   # function starts executing on line after funcdef
        # print(func_info)
        self.func_cache[func_name] = func_info
  
  def _get_value_type(self, t):
    if t == InterpreterBase.INT_DEF:
      return Value(Type.INT, 0)
    elif t == InterpreterBase.BOOL_DEF:
      return Value(Type.BOOL, 'False')
    elif t == InterpreterBase.STRING_DEF:
      return Value(Type.STRING, '""')
    elif t == InterpreterBase.REFINT_DEF:
      return Value(Type.REFINT, 0)
    elif t == InterpreterBase.REFBOOL_DEF:
      return Value(Type.REFBOOL, 'False')
    elif t == InterpreterBase.REFSTRING_DEF:
      return Value(Type.REFSTRING, '"')
    elif t == InterpreterBase.VOID_DEF:
      return InterpreterBase.VOID_DEF
