import React, { useState, useEffect } from "react";
import { useZero, useQuery } from "@rocicorp/zero/react";
import { Schema, OrderLineItem } from "../schema";
import { X, AlertTriangle } from "lucide-react";
import { ProductSelector, ProductWithStock } from "./ProductSelector";
import { ShoppingCart } from "./ShoppingCart";
import { useShoppingCartStore } from "../stores/shoppingCartStore";
import { OrderFlat } from "../api/client";

const statusOrder = [
  "CREATED",
  "PICKING",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
  "CANCELLED",
];

export interface OrderFormData {
  order_number: string;
  customer_id: string;
  store_id: string;
  order_status: string;
  order_total_amount: string;
  delivery_window_start: string;
  delivery_window_end: string;
}

const initialFormData: OrderFormData = {
  order_number: "",
  customer_id: "",
  store_id: "",
  order_status: "CREATED",
  order_total_amount: "",
  delivery_window_start: "",
  delivery_window_end: "",
};

// Extended order type with line items from Zero
export interface OrderWithLines extends OrderFlat {
  line_items?: OrderLineItem[] | null;
  line_item_count?: number | null;
  has_perishable_items?: boolean | null;
}

interface OrderFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  order?: OrderWithLines;
  onSave: (data: OrderFormData, isEdit: boolean) => void;
  isLoading: boolean;
}

export function OrderFormModal({
  isOpen,
  onClose,
  order,
  onSave,
  isLoading,
}: OrderFormModalProps) {
  const [formData, setFormData] = useState<OrderFormData>(initialFormData);
  const [showStoreChangeConfirm, setShowStoreChangeConfirm] = useState(false);
  const [pendingStoreId, setPendingStoreId] = useState<string>("");

  // 🔥 COLOCATED ZERO QUERIES - Component queries its own data
  const z = useZero<Schema>();
  const [storesData] = useQuery(z.query.stores_mv.orderBy("store_id", "asc"));
  const [customersData] = useQuery(
    z.query.customers_mv.orderBy("customer_id", "asc")
  );

  const { line_items, setStore, clearCart, addItem, getTotal, loadLineItems } =
    useShoppingCartStore();

  // Load existing line items when editing - use embedded line_items from Zero
  useEffect(() => {
    if (order && order.order_id) {
      setFormData({
        order_number: order.order_number || "",
        customer_id: order.customer_id || "",
        store_id: order.store_id || "",
        order_status: order.order_status || "CREATED",
        order_total_amount: order.order_total_amount?.toString() || "",
        delivery_window_start: order.delivery_window_start?.slice(0, 16) || "",
        delivery_window_end: order.delivery_window_end?.slice(0, 16) || "",
      });
      // Set store in cart when editing
      if (order.store_id) {
        setStore(order.store_id, true);
      }

      // Use embedded line_items from Zero (orders_with_lines_mv)
      const lineItems = order.line_items || [];

      const cartItems = lineItems.map((item) => {
        const lineAmount = item.line_amount || 0;
        const quantity = item.quantity || 0;
        // Calculate unit_price from line_amount/quantity if not provided
        const unitPrice =
          Number(item.unit_price) || (quantity > 0 ? lineAmount / quantity : 0);
        return {
          product_id: item.product_id,
          product_name: item.product_name || "Unknown Product",
          quantity: quantity,
          unit_price: unitPrice,
          perishable_flag: item.perishable_flag || false,
          available_stock: 999, // Default high stock for editing
          category: item.category || undefined,
          line_amount: lineAmount,
        };
      });

      loadLineItems(cartItems);
    } else {
      setFormData(initialFormData);
      clearCart();
    }
  }, [order, setStore, clearCart, loadLineItems]);

  // Sync cart total with form total
  useEffect(() => {
    const total = getTotal();
    if (total > 0) {
      setFormData((prev) => {
        return { ...prev, order_total_amount: total.toFixed(2) };
      });
    }
  }, [line_items, getTotal]);

  // Cleanup: clear cart when modal closes
  useEffect(() => {
    if (!isOpen) {
      clearCart();
    }
  }, [isOpen, clearCart]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate that cart is not empty for new orders
    if (!order && line_items.length === 0) {
      alert("Please add at least one product to the order");
      return;
    }

    // Calculate fresh total from cart at save time (don't rely on potentially stale form state)
    const freshTotal = getTotal();
    const dataWithFreshTotal = {
      ...formData,
      order_total_amount:
        freshTotal > 0 ? freshTotal.toFixed(2) : formData.order_total_amount,
    };

    onSave(dataWithFreshTotal, !!order);
  };

  const handleStoreChange = (newStoreId: string) => {
    // Try to set the store
    const success = setStore(newStoreId, false);

    if (!success) {
      // Store change requires confirmation
      setPendingStoreId(newStoreId);
      setShowStoreChangeConfirm(true);
    } else {
      // Store changed successfully
      setFormData({ ...formData, store_id: newStoreId });
    }
  };

  const confirmStoreChange = () => {
    setStore(pendingStoreId, true);
    setFormData({ ...formData, store_id: pendingStoreId });
    setShowStoreChangeConfirm(false);
    setPendingStoreId("");
  };

  const cancelStoreChange = () => {
    setShowStoreChangeConfirm(false);
    setPendingStoreId("");
  };

  const handleProductSelect = (product: ProductWithStock) => {
    try {
      addItem({
        product_id: product.product_id,
        product_name: product.product_name || "Unknown Product",
        quantity: 1,
        unit_price: product.unit_price || 0,
        perishable_flag: product.perishable || false,
        available_stock: product.stock_level,
        category: product.category || undefined,
      });
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to add product");
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
          <div className="flex justify-between items-center p-4 border-b">
            <h2 className="text-lg font-semibold">
              {order ? "Edit Order" : "Create Order"}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Order Number *
                </label>
                <input
                  type="text"
                  required
                  disabled={!!order}
                  value={formData.order_number}
                  onChange={(e) =>
                    setFormData({ ...formData, order_number: e.target.value })
                  }
                  placeholder="FM-1001"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 disabled:bg-gray-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status *
                </label>
                <select
                  required
                  value={formData.order_status}
                  onChange={(e) =>
                    setFormData({ ...formData, order_status: e.target.value })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                >
                  {statusOrder.map((status) => (
                    <option key={status} value={status}>
                      {status.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Customer *
                </label>
                <select
                  required
                  value={formData.customer_id}
                  onChange={(e) =>
                    setFormData({ ...formData, customer_id: e.target.value })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                >
                  <option value="">Select a customer...</option>
                  {customersData.map((customer) => (
                    <option
                      key={customer.customer_id}
                      value={customer.customer_id}
                    >
                      {customer.customer_name || "Unknown"} (
                      {customer.customer_id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Store *
                </label>
                <select
                  required
                  value={formData.store_id}
                  onChange={(e) => handleStoreChange(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                >
                  <option value="">Select a store...</option>
                  {storesData.map((store) => (
                    <option key={store.store_id} value={store.store_id}>
                      {store.store_name || "Unknown"} ({store.store_id})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Product Selector */}
            <div>
              <ProductSelector
                storeId={formData.store_id || null}
                onProductSelect={handleProductSelect}
                disabled={!formData.store_id}
              />
            </div>

            {/* Shopping Cart */}
            <div>
              <ShoppingCart />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Total Amount
                <span className="ml-2 text-xs text-gray-500">
                  (Auto-calculated from cart)
                </span>
              </label>
              <input
                type="number"
                step="0.01"
                value={formData.order_total_amount}
                readOnly
                placeholder="0.00"
                className="w-full px-3 py-2 border rounded-lg bg-gray-50 text-gray-700"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Delivery Window Start
                </label>
                <input
                  type="datetime-local"
                  value={formData.delivery_window_start}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      delivery_window_start: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Delivery Window End
                </label>
                <input
                  type="datetime-local"
                  value={formData.delivery_window_end}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      delivery_window_end: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {isLoading ? "Saving..." : order ? "Update" : "Create"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Store Change Confirmation Dialog */}
      {showStoreChangeConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4">
            <div className="flex items-start gap-3 mb-4">
              <div className="p-2 bg-orange-100 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Change Store?</h3>
                <p className="text-gray-600 text-sm">
                  Changing the store will clear all items from your cart. Are
                  you sure?
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={cancelStoreChange}
                className="px-4 py-2 text-gray-700 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmStoreChange}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
              >
                Change Store
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
