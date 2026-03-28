// ---------------------------------------------------------------------------
// Catálogo
// ---------------------------------------------------------------------------

export type ProductCategory = "pizza" | "empanada" | "drink";
export type ProductSize = "large" | "small";

export interface Product {
  id: number;
  pizzeria_id: number;
  code: string;
  short_name: string;
  full_name: string;
  description: string | null;
  category: ProductCategory;
  is_available: boolean;
  created_at: string;
}

export interface CatalogItem {
  id: number;
  pizzeria_id: number;
  product_id: number;
  size: ProductSize | null;
  price: number;
  is_active: boolean;
}

export interface ComboItem {
  id: number;
  combo_id: number;
  product_id: number;
  quantity: number;
}

export interface Combo {
  id: number;
  pizzeria_id: number;
  name: string;
  description: string | null;
  price: number;
  is_available: boolean;
  created_at: string;
}

export interface PizzeriaConfig {
  id: number;
  pizzeria_id: number;
  half_half_surcharge: number;
  welcome_message: string | null;
  opening_time: string | null;
  closing_time: string | null;
}

// ---------------------------------------------------------------------------
// WhatsApp & Empleados
// ---------------------------------------------------------------------------

export type WhatsAppSessionStatus = "connected" | "disconnected" | "scanning_qr";

export interface WhatsAppNumber {
  id: number;
  pizzeria_id: number;
  number: string;
  session_name: string;
  status: WhatsAppSessionStatus;
  is_active: boolean;
  created_at: string;
}

export type PizzeriaRole = "admin" | "cajero" | "cocinero" | "repartidor";

export interface Empleado {
  id: number;
  account_id: number;
  name: string;
  email: string;
  is_active: boolean;
  role: PizzeriaRole;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Conversaciones
// ---------------------------------------------------------------------------

export type ChatSessionStatus =
  | "active"
  | "waiting_human"
  | "transferred_human"
  | "closed";

export interface ChatMessage {
  role: "user" | "assistant" | "operator";
  content: string;
}

export interface ChatSessionDetail {
  id: number;
  pizzeria_id: number;
  customer_id: number;
  customer_phone: string;
  customer_name: string | null;
  whatsapp_number_id: number;
  whatsapp_session_name: string;
  status: ChatSessionStatus;
  messages: ChatMessage[];
  inactive_at: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Pedidos
// ---------------------------------------------------------------------------

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
