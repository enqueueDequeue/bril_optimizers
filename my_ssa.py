import sys
import time
import json


GENERATED_BLOCK_NAME_PERFIX = 'r'


class Node:
  def __init__(self, name: str,
               predecessors: list,
               successors: list) -> None:
    # name of this basic block
    self.name = name

    # labels of the basic blocks
    self.predecessors = predecessors
    self.successors = successors


def gen_rand_name() -> str:
  t = time.time()
  return f'{GENERATED_BLOCK_NAME_PERFIX}_{t}'


def get_block_name(label: str) -> str:
  return f'{label}'


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


def build_cfg(blocks: dict) -> dict:
  # label -> Node
  cfg = {}

  blocks = list(blocks.items())

  for (block_idx, (label, insts)) in enumerate(blocks):
    last_inst = insts[-1]

    if "op" in last_inst:
      op = last_inst["op"]

      if op == "br" or op == "jmp":
        target_labels = last_inst["labels"]
      elif op == "ret":
        target_labels = []
      else:
        # flows to the next block implicitly

        if block_idx + 1 < len(blocks):
          target_labels = [ blocks[block_idx + 1][0] ]
        else:
          target_labels = []

      if label not in cfg.keys():
        cfg[label] = Node(label, [], target_labels)
      else:
        cfg[label].successors = target_labels

      for target_label in target_labels:
        if target_label not in cfg.keys():
          cfg[target_label] = Node(target_label, [], [])

        target = cfg[target_label]
        target.predecessors.append(label)
    else:
      # implicit return maybe?
      if label not in cfg.keys():
        cfg[label] = Node(label, [], [])

  return cfg


def get_arg_name(arg: str, counter: int) -> str:
  return f'{arg}_{counter}'


def update_state(dest: str, state: dict, current_block_state: dict) -> int:
  count = 0

  if dest in state.keys():
    count = state[dest] + 1

  state[dest] = count

  if current_block_state is not None:
    current_block_state[dest] = count

  return count


def convert_blocks_to_ssa(entry_block: str, blocks: dict, cfg: dict,
                          state: dict = {}, block_states: dict = {},
                          out_blocks: dict = {}, ssa_sarted: list = [],
                          ssa_completed: list = []) -> dict:

  modified_insts = []

  # variable name -> [count]
  current_block_state = {}

  for predecessor in cfg[entry_block].predecessors:
    if predecessor not in block_states.keys():
      continue

    # variable and it's count
    pred_block_state = block_states[predecessor]

    for (var_name, count) in pred_block_state.items():
      if var_name in current_block_state.keys():
        # phi node is needed for this
        current_block_state[var_name].append(count)
      else:
        current_block_state[var_name] = [ count ]

  for (var_name, counters) in current_block_state.items():
    assert (0 != len(counters))

    if 1 != len(counters):
      # insert the phi node
      # todo: insert the phi node correctly
      # and get the type information correctly
      modified_insts.append(None)

      count = update_state(var_name, state)
      current_block_state[var_name] = [ count ]

  for inst in blocks[entry_block]:
    if "args" in inst.keys():
      new_args = []

      for arg in inst["args"]:
        if arg not in current_block_state.keys():
          # maybe this is the function argument
          # So, do not rename
          new_args.append(arg)
        else:
          counter = current_block_state[arg]
          new_args.append(get_arg_name(arg, counter))

      inst["args"] = new_args

    if "dest" in inst.keys():
      dest = inst["dest"]
      count = update_state(dest, state, current_block_state)
      inst["dest"] = get_arg_name(dest, count)

    modified_insts.append(inst)

  ssa_sarted.append(entry_block)

  all_predecessors_ssa_ed = True

  for predecessor in cfg[entry_block].predecessors:
    if predecessor not in ssa_sarted:
      all_predecessors_ssa_ed = False

  if all_predecessors_ssa_ed:
    ssa_completed.append(entry_block)
    out_blocks[entry_block] = modified_insts

  for successor in cfg[entry_block].successors:
    if successor not in ssa_completed:
      convert_blocks_to_ssa(successor, blocks, cfg, state, block_states, out_blocks, ssa_completed)

  return out_blocks


def convert_to_ssa(program: dict) -> dict:
  # make the blocks
  new_program = {}
  new_functions = []  

  for function in program["functions"]:
    new_function = {}
    instrs = function["instrs"]
    func_name = function["name"]
    blocks = blockify(instrs, func_name)
    cfg = build_cfg(blocks)

    for (node_label, node) in cfg.items():
      print(f'{node_label}  <- ({node.predecessors}) -> ({node.successors})')

    modified_blocks = convert_blocks_to_ssa(func_name, blocks, cfg)

    # print('----------------------------')

    modified_instrs = []

    for (block_label, _) in blocks.items():
      block_insts = modified_blocks[block_label]

      modified_instrs.extend(block_insts)

    new_function["instrs"] = modified_instrs
    new_function["name"] = func_name

    if "args" in function.keys():
      new_function["args"] = function["args"]

    if "type" in function.keys():
      new_function["type"] = function["type"]

    new_functions.append(new_function)

  new_program["functions"] = new_functions

  return new_program


if __name__ == "__main__":
  # Python dictionary beign used is expected
  # in the ordered fashion, which is a feature
  # in python 3.7 and above

  assert sys.version_info >= (3, 7)

  with open(sys.argv[1]) as source:
    program = json.load(source)
    print(json.dumps(convert_to_ssa(program)))
