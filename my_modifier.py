import sys
import json


def modify_program(program):
  inst_counter = 0
  new_program = {}
  new_functions = []

  for function in program["functions"]:
    new_function = {}
    new_instructions = []

    for instruction in function["instrs"]:
      new_instructions.append({ "op": "const", "value": inst_counter, "dest": f"myNewThingy{inst_counter}", "type": "int" })
      new_instructions.append({ "op": "print", "args": [ f"myNewThingy{inst_counter}" ] })
      new_instructions.append(instruction)

      inst_counter = inst_counter + 1

    new_function["instrs"] = new_instructions
    new_function["name"] = function["name"]
    new_function["args"] = function["args"]

    if "type" in function.keys():
      new_function["type"] = function["type"]

    new_functions.append(new_function)

  new_program["functions"] = new_functions

  return new_program


assert(2 == len(sys.argv))

with open(sys.argv[1]) as source:
  program = json.load(source)

  new_program = modify_program(program)

  print(json.dumps(new_program))
