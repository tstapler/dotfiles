function calculateTotalPrice(items: string[]): number {
  const ttlPrc = items.reduce((acc, item) => acc + item.length, 0);
  return ttlPrc;
}

function applyDiscount(basePrice: number): number {
  const ttlPrc = basePrice * 0.9;
  return ttlPrc;
}

const result = calculateTotalPrice(['apple', 'banana']);
const discounted = applyDiscount(result);
console.log(discounted);
