export type OrderStatus =
  | "in_progress"
  | "pending_payment"
  | "pending_preparation"
  | "in_preparation"
  | "ready_for_dispatch"
  | "in_delivery"
  | "delivered"
  | "cancelled"
  | "with_incident"
  | "discarded";

export type OrderOrigin = "whatsapp" | "phone" | "operator";

export interface OrderItem {
  id: number;
  order_id: number;
  product_id: number | null;
  combo_id: number | null;
  quantity: number;
  unit_price: number;
  notes: string | null;
}

export interface Order {
  id: number;
  pizzeria_id: number;
  customer_id: number;
  whatsapp_number_id: number | null;
  origin: OrderOrigin;
  status: OrderStatus;
  total: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}
