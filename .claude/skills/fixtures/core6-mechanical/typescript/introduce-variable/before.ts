interface CartItem {
  price: number;
  quantity: number;
}

const TAX_RATE = 0.08;

function getOrderSummary(items: CartItem[]): string {
  return `Order total: $${(items.reduce((sum, item) => sum + item.price * item.quantity, 0) * (1 + TAX_RATE)).toFixed(2)}`;
}

const cart: CartItem[] = [
  { price: 10.00, quantity: 2 },
  { price: 5.50, quantity: 3 },
];

console.log(getOrderSummary(cart));
