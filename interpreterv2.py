from intbase import InterpreterBase, ErrorType
from env_v2 import EnvironmentManager
from tokenize import Tokenizer
from func_v2 import FunctionManager
from val_v2 import Value, Type

# Main interpreter class
class Interpreter(InterpreterBase):
  def __init__(self, console_output=True, input=None, trace_output=False):
    super().__init__(console_output, input)
    self._setup_operations()  # setup all valid binary operations and the types they work on
    self.trace_output = trace_output

  # run a program, provided in an array of strings, one string per line of source code
  def run(self, program):
    self.program = program
    self._compute_indentation(program)  # determine indentation of every line
    self.tokenized_program = Tokenizer.tokenize_program(program)
    self.func_manager = FunctionManager(self.tokenized_program)
    self.ip = self._find_first_instruction(InterpreterBase.MAIN_FUNC)
    self.return_stack = []
    self.terminate = False
    self.env_manager = EnvironmentManager() # used to track variables/scope

    # main interpreter run loop
    while not self.terminate:
    #   print(self.env_manager)
      self._process_line()

  def _process_line(self):
    if self.trace_output:
      print(f"{self.ip:04}: {self.program[self.ip].rstrip()}")
    tokens = self.tokenized_program[self.ip]
    if not tokens:
      self._blank_line()
      return

    args = tokens[1:]

    match tokens[0]:
      case InterpreterBase.VAR_DEF:
        self._declare(args)
      case InterpreterBase.ASSIGN_DEF:
        self._assign(args)
      case InterpreterBase.FUNCCALL_DEF:
        self._funccall(args)
      case InterpreterBase.ENDFUNC_DEF:
        self._endfunc()
      case InterpreterBase.IF_DEF:
        self._if(args)
      case InterpreterBase.ELSE_DEF:
        self._else()
      case InterpreterBase.ENDIF_DEF:
        self._endif()
      case InterpreterBase.RETURN_DEF:
        self._return(args)
      case InterpreterBase.WHILE_DEF:
        self._while(args)
      case InterpreterBase.ENDWHILE_DEF:
        self._endwhile(args)
      case default:
        raise Exception(f'Unknown command: {tokens[0]}')

  def _blank_line(self):
    self._advance_to_next_statement()

  def _declare(self, args):
    if len(args) < 2:
     super().error(ErrorType.SYNTAX_ERROR,"Invalid variable statement") #no
    default_values = {'int':'0', 'bool':'False', 'string':'""'}
    value = self._get_value(default_values[args[0]])
    for var in args[1:]:
        if self.env_manager.get(var, only_curr_scope=True):
            super().error(ErrorType.NAME_ERROR,f"Redefined variable {var}", self.ip) #!
        self.env_manager.set(var, value, only_curr_scope=True)
    self._advance_to_next_statement()

  def _assign(self, args): # needs to assign to the one it finds 
    if len(args) < 2:
        super().error(ErrorType.SYNTAX_ERROR,"Invalid assignment statement") #no
    vname = args[0]
    current_val = self._get_value(vname)
    value_type = self._eval_expression(args[1:])
    if self._ref_type_checker(current_val, value_type):
        self._set_value(vname, Value(current_val.type(), value_type.value(), current_val.ref()))
        self._advance_to_next_statement()
    else:
        super().error(ErrorType.TYPE_ERROR,"Variable type and expression type do not match ", self.ip) #!

  def _funccall(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Missing function name to call", self.ip) #!
    if args[0] == InterpreterBase.PRINT_DEF:
      self._print(args[1:])
      self._advance_to_next_statement()
    elif args[0] == InterpreterBase.INPUT_DEF:
      self._input(args[1:])
      self._advance_to_next_statement()
    elif args[0] == InterpreterBase.STRTOINT_DEF:
      self._strtoint(args[1:])
      self._advance_to_next_statement()
    else:
      funcname = args[0]
      self.return_stack.append(self.ip+1)
      # set up new scope w/ passed values
      formal_parameters = self._get_function_parameters(funcname)
      actual_parameters = {}
      for i, para in enumerate(args[1:]):
        value_to_pass = self._get_value(para)
        if not self._ref_type_checker(value_to_pass, formal_parameters[i][1]):  # check if formal parameter and actual parameter types match
          super().error(ErrorType.TYPE_ERROR,f"Mismatching types {value_to_pass.type()} and {formal_parameters[i][1].type()}", self.ip) #!
        if formal_parameters[i][1].type() in [Type.REFINT, Type.REFBOOL, Type.REFSTRING]:
            actual_parameters[formal_parameters[i][0]] = Value(formal_parameters[i][1].type(), value_to_pass.value(), (para, value_to_pass))
        else:
            actual_parameters[formal_parameters[i][0]] = value_to_pass
    #   for p, v in actual_parameters.items():
    #     print(p,':', v)

      # set result to default at function level
      return_var = self._get_function_return_var(funcname)
      actual_parameters["this_is_the_reserved_result_variable"] = return_var # this is hacky but will do for now
      self.env_manager.new_func_scope(actual_parameters) # pass parameters by value
    #   print(self.env_manager)
      self.ip = self._find_first_instruction(funcname)

  def _endfunc(self):
    if not self.return_stack:  # done with main!
      self.terminate = True
    else:
      # update references
      self.env_manager.update_references()
      self.ip = self.return_stack.pop()
      self.env_manager.pop_env()

  def _if(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Invalid if syntax", self.ip) #no
    value_type = self._eval_expression(args)
    if value_type.type() != Type.BOOL:
      super().error(ErrorType.TYPE_ERROR,"Non-boolean if expression", self.ip) #!
    if value_type.value(): # if condition true
      self.env_manager.nest_new_scope() 
      self._advance_to_next_statement()
      return
    else: # if condition false
      for line_num in range(self.ip+1, len(self.tokenized_program)):
        tokens = self.tokenized_program[line_num]
        if not tokens:
          continue
        if (tokens[0] == InterpreterBase.ENDIF_DEF or tokens[0] == InterpreterBase.ELSE_DEF) and self.indents[self.ip] == self.indents[line_num]:
          self.ip = line_num + 1
          if tokens[0] == InterpreterBase.ELSE_DEF:
              self.env_manager.nest_new_scope() 
          return
    super().error(ErrorType.SYNTAX_ERROR,"Missing endif", self.ip) #no

  def _endif(self):
    self.env_manager.remove_innermost_scope()
    self._advance_to_next_statement()

  def _else(self):
    self.env_manager.nest_new_scope() 
    for line_num in range(self.ip+1, len(self.tokenized_program)):
      tokens = self.tokenized_program[line_num]
      if not tokens:
        continue
      if tokens[0] == InterpreterBase.ENDIF_DEF and self.indents[self.ip] == self.indents[line_num]:
          self.ip = line_num + 1
          return
    super().error(ErrorType.SYNTAX_ERROR,"Missing endif", self.ip) #no

  def _return(self,args):
    result_var = self._get_value("this_is_the_reserved_result_variable")
    if result_var == 'void':
        if args:
            super().error(ErrorType.TYPE_ERROR,"Return type incompatible with function declaration", self.ip) #!
        else:
            self._endfunc()
            return
    if args:
        value_type = self._eval_expression(args)
    else:
        value_type = result_var
    if not self._ref_type_checker(value_type, result_var):
        super().error(ErrorType.TYPE_ERROR,"Return type incompatible with function declaration", self.ip) #!
    result_type = self._get_result_type(value_type.t)
    self._set_value(result_type, value_type, -2)  # return passed back in resulti, resultb, results to scope above based on expression value
    self._endfunc()

  def _get_result_type(self, t):
    if t == Type.INT or t == Type.REFINT:
      return 'resulti'
    elif t == Type.BOOL or t == Type.REFBOOL:
      return 'resultb'
    elif t == Type.STRING or t == Type.REFSTRING:
      return 'results'

  def _while(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Missing while expression", self.ip) #no
    value_type = self._eval_expression(args)
    if value_type.type() != Type.BOOL:
      super().error(ErrorType.TYPE_ERROR,"Non-boolean while expression", self.ip) #!
    if value_type.value() == False:
      self._exit_while()
      return

    # If true, we advance to the next statement
    self.env_manager.nest_new_scope() # may cause problems 
    self._advance_to_next_statement()

  def _exit_while(self):
    while_indent = self.indents[self.ip]
    cur_line = self.ip + 1
    while cur_line < len(self.tokenized_program):
      if self.tokenized_program[cur_line][0] == InterpreterBase.ENDWHILE_DEF and self.indents[cur_line] == while_indent:
        self.ip = cur_line + 1
        return
      if self.tokenized_program[cur_line] and self.indents[cur_line] < self.indents[self.ip]:
        break # syntax error!
      cur_line += 1
    # didn't find endwhile
    super().error(ErrorType.SYNTAX_ERROR,"Missing endwhile", self.ip) #no

  def _endwhile(self, args):
    self.env_manager.remove_innermost_scope() # is this how we want while to scope- resets every loop?
    while_indent = self.indents[self.ip]
    cur_line = self.ip - 1
    while cur_line >= 0:
      if self.tokenized_program[cur_line][0] == InterpreterBase.WHILE_DEF and self.indents[cur_line] == while_indent:
        self.ip = cur_line
        return
      if self.tokenized_program[cur_line] and self.indents[cur_line] < self.indents[self.ip]:
        break # syntax error!
      cur_line -= 1
    # didn't find while
    super().error(ErrorType.SYNTAX_ERROR,"Missing while", self.ip) #no

  def _print(self, args):
    if not args:
      super().error(ErrorType.SYNTAX_ERROR,"Invalid print call syntax", self.ip) #no
    out = []
    for arg in args:
      val_type = self._get_value(arg)
      out.append(str(val_type.value()))
    super().output(''.join(out))

  def _input(self, args):
    if args:
      self._print(args)
    result = super().get_input()
    self.env_manager.set('results', Value(Type.STRING, result), res=True)
    # self._set_value('results', Value(Type.STRING, result))   # return always passed back in results

  def _strtoint(self, args):
    if len(args) != 1:
      super().error(ErrorType.SYNTAX_ERROR,"Invalid strtoint call syntax", self.ip) #no
    value_type = self._get_value(args[0])
    if value_type.type() != Type.STRING:
      super().error(ErrorType.TYPE_ERROR,"Non-string passed to strtoint", self.ip) #!
    self.env_manager.set('resulti', Value(Type.INT, int(value_type.value())), res=True) 
    # self._set_value('resulti', Value(Type.INT, int(value_type.value())))   # return always passed back in resulti

  def _advance_to_next_statement(self):
    # for now just increment IP, but later deal with loops, returns, end of functions, etc.
    self.ip += 1

  # create a lookup table of code to run for different operators on different types
  def _setup_operations(self):
    self.binary_op_list = ['+','-','*','/','%','==','!=', '<', '<=', '>', '>=', '&', '|']
    self.binary_ops = {}
    self.binary_ops[Type.INT] = {
     '+': lambda a,b: Value(Type.INT, a.value()+b.value()),
     '-': lambda a,b: Value(Type.INT, a.value()-b.value()),
     '*': lambda a,b: Value(Type.INT, a.value()*b.value()),
     '/': lambda a,b: Value(Type.INT, a.value()//b.value()),  # // for integer ops
     '%': lambda a,b: Value(Type.INT, a.value()%b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '>': lambda a,b: Value(Type.BOOL, a.value()>b.value()),
     '<': lambda a,b: Value(Type.BOOL, a.value()<b.value()),
     '>=': lambda a,b: Value(Type.BOOL, a.value()>=b.value()),
     '<=': lambda a,b: Value(Type.BOOL, a.value()<=b.value()),
    }
    self.binary_ops[Type.STRING] = {
     '+': lambda a,b: Value(Type.STRING, a.value()+b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '>': lambda a,b: Value(Type.BOOL, a.value()>b.value()),
     '<': lambda a,b: Value(Type.BOOL, a.value()<b.value()),
     '>=': lambda a,b: Value(Type.BOOL, a.value()>=b.value()),
     '<=': lambda a,b: Value(Type.BOOL, a.value()<=b.value()),
    }
    self.binary_ops[Type.BOOL] = {
     '&': lambda a,b: Value(Type.BOOL, a.value() and b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '|': lambda a,b: Value(Type.BOOL, a.value() or b.value())
    }
    self.binary_ops[Type.REFINT] = {
     '+': lambda a,b: Value(Type.INT, a.value()+b.value()),
     '-': lambda a,b: Value(Type.INT, a.value()-b.value()),
     '*': lambda a,b: Value(Type.INT, a.value()*b.value()),
     '/': lambda a,b: Value(Type.INT, a.value()//b.value()),  # // for integer ops
     '%': lambda a,b: Value(Type.INT, a.value()%b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '>': lambda a,b: Value(Type.BOOL, a.value()>b.value()),
     '<': lambda a,b: Value(Type.BOOL, a.value()<b.value()),
     '>=': lambda a,b: Value(Type.BOOL, a.value()>=b.value()),
     '<=': lambda a,b: Value(Type.BOOL, a.value()<=b.value()),
    }
    self.binary_ops[Type.REFSTRING] = {
     '+': lambda a,b: Value(Type.STRING, a.value()+b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '>': lambda a,b: Value(Type.BOOL, a.value()>b.value()),
     '<': lambda a,b: Value(Type.BOOL, a.value()<b.value()),
     '>=': lambda a,b: Value(Type.BOOL, a.value()>=b.value()),
     '<=': lambda a,b: Value(Type.BOOL, a.value()<=b.value()),
    }
    self.binary_ops[Type.REFBOOL] = {
     '&': lambda a,b: Value(Type.BOOL, a.value() and b.value()),
     '==': lambda a,b: Value(Type.BOOL, a.value()==b.value()),
     '!=': lambda a,b: Value(Type.BOOL, a.value()!=b.value()),
     '|': lambda a,b: Value(Type.BOOL, a.value() or b.value())
    }

  def _compute_indentation(self, program):
    self.indents = [len(line) - len(line.lstrip(' ')) for line in program]

  def _get_function_parameters(self, funcname):
    func_info = self.func_manager.get_function_info(funcname)
    if func_info == None:
      super().error(ErrorType.NAME_ERROR,f"Unable to locate {funcname} function", self.ip) #!
    return func_info.inputs

  def _find_first_instruction(self, funcname):
    func_info = self.func_manager.get_function_info(funcname)
    if func_info == None:
      super().error(ErrorType.NAME_ERROR,f"Unable to locate {funcname} function", self.ip) #!
    return func_info.start_ip

  def _get_function_return_var(self, funcname):
    func_info = self.func_manager.get_function_info(funcname)
    if func_info == None:
      super().error(ErrorType.NAME_ERROR,f"Unable to locate {funcname} function", self.ip) #!
    return func_info.return_var

  # given a token name (e.g., x, 17, True, "foo"), give us a Value object associated with it
  def _get_value(self, token):
    if not token:
      super().error(ErrorType.NAME_ERROR,f"Empty token", self.ip) #no
    if token[0] == '"':
      return Value(Type.STRING, token.strip('"'))
    if token.isdigit() or token[0] == '-':
      return Value(Type.INT, int(token))
    if token == InterpreterBase.TRUE_DEF or token == InterpreterBase.FALSE_DEF:
      return Value(Type.BOOL, token == InterpreterBase.TRUE_DEF)
    value = self.env_manager.get(token)
    if value  == None:
      super().error(ErrorType.NAME_ERROR,f"Unknown variable {token}", self.ip) #!
    return value

  # given a variable name and a Value object, associate the name with the value
  def _set_value(self, varname, value, scope=None): # TODO: use kwargs
    if scope is None:
        self.env_manager.set(varname, value)
    else:
        self.env_manager.set(varname, value, scope)

  # evaluate expressions in prefix notation: + 5 * 6 x
  def _eval_expression(self, tokens):
    stack = []

    for token in reversed(tokens):
      if token in self.binary_op_list:
        v1 = stack.pop()
        v2 = stack.pop()
        if not self._ref_type_checker(v1, v2):
        # if v1.type() != v2.type():
          super().error(ErrorType.TYPE_ERROR,f"Mismatching types {v1.type()} and {v2.type()}", self.ip) #!
        operations = self.binary_ops[v1.type()]
        if token not in operations:
          super().error(ErrorType.TYPE_ERROR,f"Operator {token} is not compatible with {v1.type()}", self.ip) #!
        stack.append(operations[token](v1,v2))
      elif token == '!':
        v1 = stack.pop()
        if v1.type() != Type.BOOL and v1.type() != Type.REFBOOL:
          super().error(ErrorType.TYPE_ERROR,f"Expecting boolean for ! {v1.type()}", self.ip) #!
        stack.append(Value(v1.type(), not v1.value()))
      else:
        value_type = self._get_value(token)
        stack.append(value_type)

    if len(stack) != 1:
      super().error(ErrorType.SYNTAX_ERROR,f"Invalid expression", self.ip) #no

    return stack[0]

  def _ref_type_checker(self, v1, v2):
    if v1.type() != v2.type():
        if v1.type() in [Type.INT, Type.REFINT] and v2.type() in [Type.INT, Type.REFINT]:
            return True
        elif v1.type() in [Type.STRING, Type.REFSTRING] and v2.type() in [Type.STRING, Type.REFSTRING]:
            return True
        elif v1.type() in [Type.BOOL, Type.REFBOOL] and v2.type() in [Type.BOOL, Type.REFBOOL]:
            return True
        else:
            return False
    return True


'Verify that there are no corner cases where scopes are not entered/exited properly.'

l = ['func main void',
'  if True',
'    while False',
'        funccall print 1',
'    endwhile',
'  else',
'     var int e',
'     assign e -32',
'  endif',
'  funccall print e',
'endfunc']


results_test_case = [
'func main void',
'    assign a 9',
'    funccall input "enter your name"',
'    if True',
'        funccall input "enter mid name "',
'        funccall print results',
'    endif',
'    funccall print results',

'endfunc']

nesting_case = [
'func main void',
'  var int a',
'  assign a 1',
'  while < a 3',
'    var int c',
'    if == a 11',
'      funccall print "never"',
'    else',
'      while < c 2',
'        var int b',
'        var bool a',
'        funccall print "b " b',
'        assign c + c 1',
'        funccall print "c " c',
'      endwhile',
'      assign a + a 1',
'    endif',
'  endwhile',
'  funccall print a',
'endfunc']

output_6 = [
'func main void',
' var int a',
' assign a 5',
' funccall foo a',
' assign resulti 7',
' funccall print a',
'endfunc',
'',
'func foo b:refint int',
' assign b + 1 b',
' return b',
'endfunc'
]

doublemod = [
'func main void',
'var int a',
'funccall doublemod a a',
'funccall print a',
'endfunc',
'',
'func doublemod a:refint b:refint void',
'assign a + a 5',
'assign b + b 10',
'endfunc']


def main():
    input = doublemod

    i = Interpreter(trace_output=True)
    i.run(input)

main()

'func main void',
' var int a',
' assign a 2',
'endfunc',
'',
'func foo x:refint void',
'  funccall bar x',
'endfunc',
'func bar y:refint void',
'  funccall print y',
'endfunc'



#    'func main void',
#     '    var int a',
#     '    assign a 1 ',
#     '    funccall test a True',
#     '    funccall print a',
#     'endfunc',
#     'func test x:refint y:bool void',
#     '    funccall print x " " y',
#     '    assign x + x 1',
#     '    funccall print x',
#     'endfunc'

# 'func foo a:int b:int c:int void',
# '  assign a 1',
# '  assign b 1',
# '  assign c 1',
# '  funccall print a " " b " " c',
# 'endfunc',
# '',
# '',
# 'func main void',
# '  var int a b c',
# '  assign a 2',
# '  assign b 2',
# '  assign c 2',
# '  funccall print a " " b " " c',
# '  funccall foo a b c',
# '  funccall print a " " b " " c',
# 'endfunc'


# 'func main void',
# ' var int v1',
# ' assign v1 + 20 True',
# ' funccall print v1',
# 'endfunc'

# 'func main void',
# '  var string s',
# '  var int n',
# '  funccall input "Enter a number: "',
# '  funccall strtoint results',
# '  assign n + resulti 1',
# '  funccall print n',
# 'endfunc'

# 'func main void',
# ' var int v1',
# ' assign v1 + 20 True',
# ' funccall print v1',
# 'endfunc'


# 'func foo x:int int',
# ' return x',
# 'endfunc',
# '',
# 'func main void',
# ' var int a',
# ' assign a 5',
# ' funccall foo a',
# ' assign resulti 10',
# ' funccall print a ',
# ' assign a 20',
# ' funccall print resulti',
# 'endfunc'

# 'func main void',
# '  var int a',
# '  assign a 5',
# '  if True',
# '   funccall print a',
# '   var string b',
# '   assign b "foobar"',
# '   if True',
# '    funccall print a ',
# '    funccall print b',
# '    var int b',
# '    assign b 1',
# '    while > b 0',
# '     var bool c',
# '     assign c True',
# '     funccall print a " " b " " c',
# '     assign b - b 1',
# '    endwhile',
# '   endif',
# '   funccall print b',
# '  endif',
# 'endfunc'

# ['func ifunc n:int int',
# ' return n ',
# 'endfunc',
# ' ',
# 'func sfunc s:string string',
# ' return s',
# 'endfunc',
# '',
# 'func bfunc b:bool bool',
# ' return b',
# 'endfunc',
# '',
# 'func main void',
# '  var int i',
# '  var string s',
# '  var bool b',
# '',
# '  funccall ifunc 42',
# '  assign i resulti',
# '  funccall print i',
# ' ',
# '  funccall sfunc "foo"',
# '  assign s results',
# '  funccall print s',
# ' ',
# '  funccall bfunc True',
# '  assign b resultb',
# '  funccall print b',
# ' ',
# 'endfunc']


# 'func main void',
# ' var int a b',
# ' assign a 5',
# ' assign b 100',
# ' funccall print a " " b',
# ' if True',
# '  assign a 10',
# '  funccall print a " " b',
# '  var int a',
# '  assign a 6',
# '  funccall print a " " b',
# '  var int b',
# '  assign b -1',
# '  funccall print a " " b',
# ' endif',
# ' funccall print a " " b',
# 'endfunc'




# 'func main void',
# ' var int a b',
# ' assign a 5',
# ' assign b 100',
# ' funccall print a " " b',
# ' if True',
# '  assign a 10',
# '  funccall print a " " b',
# '  var int a',
# '  assign a 6',
# '  funccall print a " " b',
# '  var int b',
# '  assign b -1',
# '  funccall print a " " b',
# ' endif',
# ' funccall print a " " b',
# 'endfunc'


# 'func main void',
# '  var int x',
# '  var string y',
# '  var bool z',
# '  assign x 42',
# '  assign y "foo"',
# '  assign z True ',
# '  funccall foo x y z',
# '  funccall print x " " y " " z',
# '  funccall bletch',
# '  funccall bar resulti',
# '  funccall print resulti',
# 'endfunc',
# '',
# 'func foo a:refint b:refstring c:refbool void',
# ' assign a -42',
# ' assign b "bar"',
# ' assign c False',
# 'endfunc',
# '',
# 'func bletch int',
# ' return 100',
# 'endfunc',
# '',
# 'func bar a:refint void',
# ' assign a -100 ',
# 'endfunc'


# 'func main void',
# '    var int n',
# '    assign n 4',
# '    var string result',
# '    assign result "a"',
# '    funccall double result n',
# '    funccall print result',
# '',
# '    assign n 6',
# '    assign result "##"',
# '    funccall double result n',
# '    funccall print result',
# '',
# 'endfunc',
# '',
# 'func double result:refstring n:int void',
# '    if == n 0',
# '        return',
# '    endif',
# '    assign n - n 1',
# '    assign result + result result',
# '    funccall double result n',
# 'endfunc'
