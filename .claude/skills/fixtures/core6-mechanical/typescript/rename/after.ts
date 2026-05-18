function calculateTotalPrice(items: string[]): number {
  const totalPrice = items.reduce((acc, item) => acc + item.length, 0);
  return totalPrice;
}

function applyDiscount(basePrice: number): number {
  const totalPrice = basePrice * 0.9;
  return totalPrice;
}

const result = calculateTotalPrice(['apple', 'banana']);
const discounted = applyDiscount(result);
console.log(discounted);
