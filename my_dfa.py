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
  return label


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

  for (label, insts) in blocks.items():
    last_inst = insts[-1]

    if "op" in last_inst:
      op = last_inst["op"]

      if op == "br" or op == "jmp":
        target_labels = last_inst["labels"]
      elif op == "ret":
        target_labels = []
      else:
        # implicit return maybe
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


def find_all_blocks_which_ret(cfg: dict) -> list:
  blocks_ret = []

  for (label, node) in cfg.items():
    if 0 == len(node.successors):
      blocks_ret.append(label)

  return blocks_ret


def live_variables_analysis(cfg: dict, blocks: dict):
  total_uses = {}

  work_list = find_all_blocks_which_ret(cfg)

  print(f'work_list: {work_list}')

  while True:
    if 0 == len(work_list):
      break

    current_label = work_list.pop(0)
    current_node = cfg[current_label]

    for pred in current_node.predecessors:
      if pred not in work_list:
        work_list.append(pred)

    uses = []

    for inst in blocks[current_label]:
      uses.extend(inst["args"] if "args" in inst else [])

    final_uses = []

    final_uses.extend(uses)

    for successor in current_node.successors:
      if successor not in total_uses.keys():
        print("error in the algorithm")
        exit(1)
      else:
        final_uses.extend(total_uses[successor])

    total_uses[current_label] = final_uses

  return total_uses


def analyze(program: dict) -> None:
  for function in program["functions"]:
    blocks = blockify(function["instrs"], function["name"])
    cfg = build_cfg(blocks)
    lv = live_variables_analysis(cfg, blocks)

    print('')

    for (label, node) in cfg.items():
      assert label == node.name
      print(f'{label} -->')
      print(f'pred: {node.predecessors}')
      print(f'succ: {node.successors}')
      print('---------------------------------------')

    print('')

    for (label, _) in blocks.items():
      if label in lv.keys():
        print(f'{label}:\t {set(lv[label])}')
      else:
        # not all labels are necessarily be present
        # some labels might not have any instructions
        # and be empty
        print(f'{label}: not found')


if __name__ == "__main__":
  # Python dictionary beign used is expected
  # in the ordered fashion, which is a feature
  # in python 3.7 and above

  assert sys.version_info >= (3, 7)

  with open(sys.argv[1]) as source:
    program = json.load(source)
    analyze(program)
