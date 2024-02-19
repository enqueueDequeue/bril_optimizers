import sys
import time
import json
import numbers


ACTUAL_BLOCK_NAME_PERFIX = 'o'
GENERATED_BLOCK_NAME_PERFIX = 'r'


class Code:
  def __init__(self) -> None:
    self.is_const = False
    self.is_commutive = False

  def __eq__(self, _: object) -> bool:
    return False


class ID(Code):
  def __init__(self, id: int) -> None:
    super().__init__()

    print(f"id: {id}")
    self.id = id

  def __eq__(self, other: object) -> bool:
    if isinstance(other, ID):
      return self.id == other.id

    return False


class Const(Code):
  def __init__(self, value: numbers.Number) -> None:
    super().__init__()

    self.is_const = True
    self.value = value

  def __eq__(self, other: object) -> bool:
    if isinstance(other, Const):
      return self.value == other.value

    return False


class Arithematic(Code):
  def __init__(self, op: str, args: list, is_commutive: bool = True) -> None:
    super().__init__()

    self.op = op
    self.is_commutive = is_commutive
    self.args = args.copy()

    if is_commutive:
      self.args.sort()

  def __eq__(self, other: object) -> bool:
    if isinstance(other, Arithematic):
      return self.op == other.op and self.args == other.args

    return False


class NonDeterminant(Code):
  def __init__(self, args: list) -> None:
    super().__init__()

    self.args = args


class Determinant(Code):
  def __init__(self, symbol: str) -> None:
    super().__init__()

    self.symbol = symbol

  def __eq__(self, other: object) -> bool:
    if isinstance(other, Determinant):
      return self.symbol == other.symbol

    return False


class RenameEntry:
  def __init__(self, code: Code, name: str) -> None:
    self.code = code
    self.name = name


def gen_rand_name() -> str:
  t = time.time()
  return f'{GENERATED_BLOCK_NAME_PERFIX}_{t}'


def get_block_name(label: str) -> str:
  return f'{ACTUAL_BLOCK_NAME_PERFIX}_{label}'


def blockify(insts: list, func: str) -> dict:
  blocks = {}

  current_block_name = get_block_name(func)
  current_block_insts = []

  for inst in insts:
    if "op" in inst.keys():
      op = inst["op"]

      if op == "br" or op == "jmp" or op == "ret":
        current_block_insts.append(inst)

        blocks[current_block_name] = current_block_insts

        current_block_name = gen_rand_name()
        current_block_insts = []        
      else:
        current_block_insts.append(inst)

    elif "label" in inst.keys():
      if current_block_insts:
        blocks[current_block_name] = current_block_insts

      current_block_name = get_block_name(inst["label"])
      current_block_insts = [ inst ]
    else:
      print(f"Illegal instruction detected: {inst}")
      exit(1)

  if current_block_insts:
    blocks[current_block_name] = current_block_insts

  return blocks


def unblockify(block: dict) -> list:
  func_insts = []

  for (_, block_insts) in block.items():
    func_insts.extend(block_insts)

  return func_insts


# todo: this is not perfect, any symbols with
#       name collisions will cause issues
def get_arg_name(arg: str, counter: int) -> str:
  if 1 == counter:
    return arg
  else:
    return f'{arg}_{counter}'


def block_rename(insts: list) -> list:
  renamed_insts = []
  dest_counter = {}

  for inst in insts:
    inst = inst.copy()

    if "args" in inst.keys():
      new_args = []

      for arg in inst["args"]:
        if arg not in dest_counter.keys():
          # maybe this is the function argument
          # So, do not rename
          new_args.append(arg)
        else:
          (counter, _) = dest_counter[arg]
          new_args.append(get_arg_name(arg, counter))

      inst["args"] = new_args

    if "dest" in inst.keys():
      dest = inst["dest"]

      if dest in dest_counter.keys():
        counter, dest_type = dest_counter[dest]
      else:
        assert "type" in inst.keys()
        counter, dest_type = (0, inst["type"])

      counter = counter + 1

      inst["dest"] = get_arg_name(dest, counter)

      if "type" not in inst.keys():
        inst["type"] = dest_type

      dest_counter[dest] = (counter, dest_type)

    renamed_insts.append(inst)

  return renamed_insts


def dce_insts(input_insts: list) -> list:
  insts = []
  insts.extend(block_rename(input_insts))

  while True:
    dce_insts = []
    variables_used = []

    for inst in insts:
      if "args" in inst.keys():
        variables_used.extend(inst["args"])

    for inst in insts:
      if "dest" in inst.keys():
        dest = inst["dest"]

        if dest in variables_used:
          dce_insts.append(inst)
      else:
        dce_insts.append(inst)

    if insts == dce_insts:
      # converged, let's return
      break
    else:
      # continue to iterate till convergence
      insts = dce_insts

  return insts


def dce(program: dict) -> dict:
  new_program = {}
  new_functions = []

  for function in program["functions"]:
    new_function = {}

    dce_blocks = {}
    og_blocks = blockify(function["instrs"], function["name"])

    # print('------------------------------------')
    # print(f'{function["name"]}:')
    # print(f'{og_blocks}')
    # print('------------------------------------')

    # delete the blocks which are not jump targets
    for (label, insts) in og_blocks.items():

      assert label.startswith(ACTUAL_BLOCK_NAME_PERFIX) \
              or label.startswith(GENERATED_BLOCK_NAME_PERFIX)

      if label.startswith(ACTUAL_BLOCK_NAME_PERFIX):
        dce_blocks[label] = insts

    new_function["instrs"] = dce_insts(unblockify(dce_blocks))
    new_function["name"] = function["name"]

    if "args" in function.keys():
      new_function["args"] = function["args"]

    if "type" in function.keys():
      new_function["type"] = function["type"]

    new_functions.append(new_function)

  new_program["functions"] = new_functions

  return new_program


def find_entry(entry: RenameEntry, table: list) -> int:
  index = -1

  for (i, item) in enumerate(table):
    if item.code == entry.code:
      assert (index == -1)
      index = i

  return index


def block_lvn(insts: list, table: list, state: dict, func_args: list) -> list:
  trim_insts = []

  # id -> RenameEntry(Code, canonical name)
  # table = []

  # variable -> id
  # state = {}

  for func_arg in func_args:
    entry = RenameEntry(Determinant(func_arg), func_arg)

    index = find_entry(entry, table)

    if -1 == index:
      id = len(table)
      table.append(entry)
      state[func_arg] = id
    else:
      id = index
      state[func_arg] = index

  for inst in insts:
    # print(f'inst: {inst}')

    if "dest" not in inst.keys():
      trim_insts.append(inst)
      continue

    trim_inst = None
    dest = inst["dest"]
    args = [] if "args" not in inst.keys() else inst["args"]
    entry_args = [ state[arg] for arg in args ]

    if "op" not in inst.keys():
      # dest present AND op is not present
      # this case shouldn't be possible
      # Just here to make sure of the dirty code

      entry = RenameEntry(NonDeterminant(inst, entry_args), dest)

      id = len(table)
      table.append(entry)
      state[dest] = id

      trim_inst = inst
    else:
      op = inst["op"]

      if op == "id":
        assert (1 == len(args))

        entry_id = state[args[0]]
        state[dest] = entry_id
      elif op == "const":
        assert "value" in inst.keys()

        entry = RenameEntry(Const(inst["value"]), dest)

        index = find_entry(entry, table)

        if -1 == index:
          # not found, insert
          id = len(table)
          table.append(entry)
          state[dest] = id

          trim_inst = inst
        else:
          # const already present, reuse it
          id = index
          state[dest] = id
      elif op == "add":
        entry = RenameEntry(Arithematic(op, entry_args), dest)

        index = find_entry(entry, table)

        if -1 == index:
          # not found, insert
          id = len(table)
          table.append(entry)
          state[dest] = id

          trim_inst = inst
        else:
          id = index
          state[dest] = id
      elif op == "mul":
        entry = RenameEntry(Arithematic(op, entry_args), dest)

        index = find_entry(entry, table)

        if -1 == index:
          # not found, insert
          id = len(table)
          table.append(entry)
          state[dest] = id

          trim_inst = inst
        else:
          id = index
          state[dest] = id
      elif op == "sub":
        entry = RenameEntry(Arithematic(op, entry_args, False), dest)

        index = find_entry(entry, table)

        if -1 == index:
          # not found, insert
          id = len(table)
          table.append(entry)
          state[dest] = id

          trim_inst = inst
        else:
          id = index
          state[dest] = id
      elif op == "div":
        entry = RenameEntry(Arithematic(op, entry_args, False), dest)

        index = find_entry(entry, table)

        if -1 == index:
          # not found, insert
          id = len(table)
          table.append(entry)
          state[dest] = id

          trim_inst = inst
        else:
          id = index
          state[dest] = id
      else:
        entry = RenameEntry(NonDeterminant(entry_args), dest)

        id = len(table)
        table.append(entry)
        state[dest] = id

        trim_inst = inst

    if trim_inst is not None:
      trim_insts.append(trim_inst)

  # rename the args with the new ones for each instruction
  for trim_inst in trim_insts:
    if "args" in trim_inst.keys():
      trim_args = []

      for arg in trim_inst["args"]:
        if arg not in state:
          trim_args.append(arg)
        else:
          trim_args.append(table[state[arg]].name)

      trim_inst["args"] = trim_args

  return trim_insts


def lvn(program: dict) -> dict:
  new_program = {}
  new_functions = []

  for function in program["functions"]:
    new_function = {}
    function_args = [ arg["name"] for arg in ([] if "args" not in function.keys() else function["args"]) ]

    trim_blocks = {}
    og_blocks = blockify(function["instrs"], function["name"])

    table = []
    state = {}

    for (label, insts) in og_blocks.items():
      trim_blocks[label] = block_lvn(insts, table, state, function_args)

    new_function["instrs"] = unblockify(trim_blocks)
    new_function["name"] = function["name"]

    if "args" in function.keys():
      new_function["args"] = function["args"]

    if "type" in function.keys():
      new_function["type"] = function["type"]

    new_functions.append(new_function)

  new_program["functions"] = new_functions

  return new_program


def optimize(program: dict) -> dict:
  while True:
    optimized_program = lvn(dce(program))

    if optimized_program == program:
      return optimized_program
    else:
      program = optimized_program


if __name__ == "__main__":
  # Python dictionary beign used is expected
  # in the ordered fashion, which is a feature
  # in python 3.7 and above

  assert sys.version_info >= (3, 7)

  assert(2 == len(sys.argv))

  with open(sys.argv[1]) as source:
    program = json.load(source)

    optimized_program = optimize(program)

    print(json.dumps(optimized_program, indent=2, sort_keys=True))
