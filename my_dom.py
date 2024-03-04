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


def find_dominators(node: str, cfg: dict, strict_dominators: set) -> str:
  prev_node = None
  current_node = node

  dominator = None

  seen = set()

  while prev_node != current_node:
    # print(f'{current_node}')
    pred = current_node

    if current_node in seen:
      break

    if 0 != len(cfg[current_node].predecessors):
      found = False

      for pred in cfg[current_node].predecessors:
        if pred in strict_dominators:
          dominator = pred
          found = True

      if found:
        break

    seen.add(current_node)

    prev_node = current_node
    current_node = pred

  return dominator


def build_dom(blocks: dict, cfg: dict) -> None:
  # block_label -> (dominators)
  dom = {}
  current_dom = {}

  # initialize dom with all blocks for each block
  all_blocks = set()

  for (label, _) in blocks.items():
    all_blocks.add(label)

  for (label, _) in blocks.items():
    current_dom[label] = set(all_blocks)

  while dom != current_dom:
    dom = {}

    for (node_label, dominators) in current_dom.items():
      dom[node_label] = set(dominators)

    for (node_label, node) in cfg.items():
      dom_entry = set()

      # get the union of all preds
      for pred in node.predecessors:
        dom_entry = dom_entry.union(current_dom[pred])

      # now get the intersection
      for pred in node.predecessors:
        dom_entry = dom_entry.intersection(current_dom[pred])

      dom_entry.add(node_label)

      current_dom[node_label] = dom_entry

  print('')
  print('dominators:')

  # printing the dominators of each block
  for (master, slaves) in dom.items():
    slaves = list(slaves)
    slaves.sort()

    print(f'{master}: \t\t{", ".join(slaves)}')

  print('')
  print('dominance tree:')

  # building the dominator tree
  dom_tree = {}

  for (node_label, dominators) in dom.items():
    strict_dominators = set(dominators)

    strict_dominators.remove(node_label)

    dom_tree[node_label] = find_dominators(node_label, cfg, strict_dominators)

  for (node, dominator) in dom_tree.items():
    print(f'{node}: \t\t{dominator}')

  print('')
  print('dominance frontier:')

  # building the dominance frontier
  dom_frontier = {}

  for (node_label, dominators) in dom.items():

    frontier = []

    for succ in cfg[node_label].successors:
      strict_dominators = set(dom[succ])

      strict_dominators.remove(succ)

      if node_label != find_dominators(succ, cfg, strict_dominators):
        frontier.append(succ)

    dom_frontier[node_label] = frontier

  for (node, frontier) in dom_frontier.items():
    print(f'{node}: \t\t{frontier}')


def build_dom_tree(program: dict) -> None:
  for function in program["functions"]:
    blocks = blockify(function["instrs"], function["name"])
    cfg = build_cfg(blocks)

    for (node_label, node) in cfg.items():
      print(f'{node_label}  <- ({node.predecessors}) -> ({node.successors})')

    print("")

    build_dom(blocks, cfg)


if __name__ == "__main__":
  # Python dictionary beign used is expected
  # in the ordered fashion, which is a feature
  # in python 3.7 and above

  assert sys.version_info >= (3, 7)

  with open(sys.argv[1]) as source:
    program = json.load(source)
    build_dom_tree(program)
