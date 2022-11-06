# The EnvironmentManager class keeps a mapping between each global variable (aka symbol)
# in a brewin program and the value of that variable - the value that's passed in can be
# anything you like. In our implementation we pass in a Value object which holds a type
# and a value (e.g., Int, 10).
class EnvironmentManager:
  def __init__(self):
    self.environment = [[{}]] # list of list of dictionaries
    # where outer list is function scopes, inner list is block scopes, dictionary contains the variables

  def __str__(self):
    return self.environment.__str__()

  # Gets the data associated a variable name
  def get(self, symbol, only_curr_scope=False):
    if only_curr_scope:
      return self.environment[-1][-1].get(symbol, None)
    for env in self.environment[-1][::-1]:
      data = env.get(symbol, None)
      if data is not None:
        return data

  # Sets the data associated with a variable name
  def set(self, symbol, value, func_scope=-1, only_curr_scope=False, res=False):
    if func_scope == -1 and not res:
      if only_curr_scope:
        self.environment[-1][-1].update({symbol:value})
      for env in self.environment[-1][::-1]:
        data = env.get(symbol, None)
        if data is not None:
          env.update({symbol:value})
          return
    else:
      self.environment[func_scope][0].update({symbol:value})

  def new_func_scope(self, params={}):
    self.environment.append([params])
  
  def pop_env(self):
    self.environment.pop()
  
  def nest_new_scope(self):
    self.environment[-1].append({})
  
  def remove_innermost_scope(self):
    self.environment[-1].pop()