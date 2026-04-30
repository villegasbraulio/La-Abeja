import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CartItem {
  wineId: string;
  slug: string;
  name: string;
  price: string;
  primaryImage: string | null;
  varietalName: string;
  vintageYear: number;
  quantity: number;
}

export interface CartProduct {
  wineId: string;
  slug: string;
  name: string;
  price: string;
  primaryImage: string | null;
  varietalName: string;
  vintageYear: number;
}

interface CartState {
  items: CartItem[];
  addItem: (product: CartProduct) => void;
  removeItem: (wineId: string) => void;
  updateQuantity: (wineId: string, quantity: number) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      addItem: (product) =>
        set((state) => {
          const existing = state.items.find((item) => item.wineId === product.wineId);
          if (existing) {
            return {
              items: state.items.map((item) =>
                item.wineId === product.wineId
                  ? { ...item, quantity: item.quantity + 1 }
                  : item,
              ),
            };
          }
          return {
            items: [...state.items, { ...product, quantity: 1 }],
          };
        }),
      removeItem: (wineId) =>
        set((state) => ({
          items: state.items.filter((item) => item.wineId !== wineId),
        })),
      updateQuantity: (wineId, quantity) =>
        set((state) => ({
          items:
            quantity <= 0
              ? state.items.filter((item) => item.wineId !== wineId)
              : state.items.map((item) =>
                  item.wineId === wineId ? { ...item, quantity } : item,
                ),
        })),
      clearCart: () => set({ items: [] }),
    }),
    {
      name: "bodega-la-abeja-cart",
    },
  ),
);
