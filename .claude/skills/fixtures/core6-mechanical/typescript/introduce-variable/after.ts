interface CartItem {
  price: number;
  quantity: number;
}

const TAX_RATE = 0.08;

function getOrderSummary(items: CartItem[]): string {
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const totalWithTax = subtotal * (1 + TAX_RATE);
  return `Order total: $${totalWithTax.toFixed(2)}`;
}

const cart: CartItem[] = [
  { price: 10.00, quantity: 2 },
  { price: 5.50, quantity: 3 },
];

console.log(getOrderSummary(cart));
