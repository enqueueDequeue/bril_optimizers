# Compile the typescript code to bril json

- Make sure to add the deno bin to path: `PATH=$PATH:$HOME/.deno/bin:$HOME/Library/Python/3.9/bin`
- This adds `ts2bril` and `brili` commands to the PATH
- And, `bril2json` & `bril2txt` from python's flit are also added to the PATH
- Compile the ts code to bril using `ts2bril my_benchmark.ts > my_benchmark.json`
- Run the json using `brili` (bril interpreter) `brili < my_benchmark.json`
- Delete the json files `rm *.json`
- Check [bril](https://github.com/sampsyo/bril) for more instructions
