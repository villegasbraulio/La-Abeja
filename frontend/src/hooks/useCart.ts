import { useCartStore } from "../store/cartStore";
import { formatARS } from "../lib/utils";

export function useCart() {
  const items = useCartStore((state) => state.items);
  const addItem = useCartStore((state) => state.addItem);
  const removeItem = useCartStore((state) => state.removeItem);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const clearCart = useCartStore((state) => state.clearCart);
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);
  const subtotal = items.reduce(
    (sum, item) => sum + Number.parseFloat(item.price) * item.quantity,
    0,
  );

  return {
    items,
    itemCount,
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    subtotal,
    subtotalFormatted: formatARS(subtotal),
  };
}
