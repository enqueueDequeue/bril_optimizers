function add(x: number, y: number): number {
  return x + y;
}

function print(x: number) {
  console.log(x);
}

var x: number = 5;
var y: number = 6;
var sum: number = add(x, y);

if (11 == sum) {
  console.log(101);
} else {
  console.log(102);
}

print(sum);
