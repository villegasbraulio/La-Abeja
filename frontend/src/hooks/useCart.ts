import { useCartStore } from "../store/cartStore";
import { formatARS } from "../lib/utils";
import { useToastStore } from "../store/toastStore";

export function useCart() {
  const items = useCartStore((state) => state.items);
  const addItemToStore = useCartStore((state) => state.addItem);
  const removeItemFromStore = useCartStore((state) => state.removeItem);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const clearCartFromStore = useCartStore((state) => state.clearCart);
  const showToast = useToastStore((state) => state.showToast);
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);
  const subtotal = items.reduce(
    (sum, item) => sum + Number.parseFloat(item.price) * item.quantity,
    0,
  );

  function addItem(product: Parameters<typeof addItemToStore>[0]) {
    const existing = items.find((item) => item.wineId === product.wineId);

    addItemToStore(product);
    showToast({
      variant: "success",
      title: existing ? "Sumamos otra botella al carrito" : "Vino agregado al carrito",
      description: existing
        ? `${product.name} ahora tiene ${existing.quantity + 1} botella(s) en tu selección.`
        : `${product.name} ya está listo para comprar cuando quieras.`,
    });
  }

  function removeItem(wineId: string) {
    const item = items.find((currentItem) => currentItem.wineId === wineId);

    removeItemFromStore(wineId);

    if (!item) {
      return;
    }

    showToast({
      variant: "info",
      title: "Quitamos el vino del carrito",
      description: `${item.name} salió de tu selección.`,
    });
  }

  function clearCart() {
    if (items.length === 0) {
      return;
    }

    clearCartFromStore();
    showToast({
      variant: "info",
      title: "Carrito vaciado",
      description: "Dejamos tu selección lista para volver a empezar.",
    });
  }

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
