// ─── Lauren Eats - AI Restaurant Platform Types ────────────────────────

// ─── Enums ────────────────────────────────────────────────────────────

export enum AgentType {
  Concierge = "concierge",
  FoodRecommender = "food_recommender",
  Dietary = "dietary",
  Ordering = "ordering",
  Reservation = "reservation",
  Support = "support",
}

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "preparing"
  | "ready"
  | "delivered"
  | "cancelled";

export type OrderType = "dine_in" | "takeout" | "delivery";

export type ReservationStatus =
  | "pending"
  | "confirmed"
  | "cancelled"
  | "completed";

export type Occasion =
  | "birthday"
  | "anniversary"
  | "business"
  | "casual";

export type MessageRole = "user" | "assistant" | "system" | "tool";

export type SpicyLevel = 0 | 1 | 2 | 3 | 4 | 5;

export type FeedbackCategory = "food" | "service" | "ambiance" | "overall";

export type UserRole = "customer" | "admin" | "staff";

// ─── Core Models (aligned with Prisma schema) ─────────────────────────

export interface Category {
  id: string;
  name: string;
  nameZh: string | null;
  slug: string;
  description: string | null;
  icon: string | null;
  sortOrder: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  menuItems?: MenuItem[];
}

export interface MenuItem {
  id: string;
  name: string;
  nameZh: string | null;
  description: string;
  price: number;
  image: string | null;
  categoryId: string;
  spicyLevel: SpicyLevel;
  isVegetarian: boolean;
  isVegan: boolean;
  isGlutenFree: boolean;
  isPopular: boolean;
  isAvailable: boolean;
  calories: number | null;
  preparationTime: number | null;
  ingredients: string | null; // JSON array string
  allergens: string | null; // JSON array string
  tags: string | null; // JSON array string
  createdAt: string;
  updatedAt: string;
  category?: Category;
}

export interface Order {
  id: string;
  userId: string | null;
  orderNumber: string;
  status: OrderStatus;
  totalAmount: number;
  subtotal: number;
  tax: number;
  discount: number;
  notes: string | null;
  type: OrderType;
  tableNumber: string | null;
  createdAt: string;
  updatedAt: string;
  user?: User | null;
  orderItems: OrderItem[];
}

export interface OrderItem {
  id: string;
  orderId: string;
  menuItemId: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  notes: string | null;
  createdAt: string;
  order?: Order;
  menuItem?: MenuItem;
}

export interface Reservation {
  id: string;
  userId: string | null;
  customerName: string;
  customerPhone: string;
  customerEmail: string | null;
  partySize: number;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  status: ReservationStatus;
  tableNumber: string | null;
  specialRequests: string | null;
  occasion: Occasion | null;
  createdAt: string;
  updatedAt: string;
  user?: User | null;
}

export interface Conversation {
  id: string;
  userId: string | null;
  title: string | null;
  agentType: AgentType | null;
  status: "active" | "ended";
  metadata: string | null; // JSON string
  createdAt: string;
  updatedAt: string;
  user?: User | null;
  messages?: AgentMessage[];
}

export interface AgentMessage {
  id: string;
  conversationId: string;
  role: MessageRole;
  content: string;
  agentType: AgentType | null;
  toolCalls: string | null; // JSON
  toolResults: string | null; // JSON
  metadata: string | null; // JSON
  createdAt: string;
  conversation?: Conversation;
}

export interface Feedback {
  id: string;
  userId: string | null;
  rating: number; // 1-5
  comment: string | null;
  category: FeedbackCategory | null;
  orderId: string | null;
  createdAt: string;
  user?: User | null;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  avatar: string | null;
  role: UserRole;
  preferences: string | null; // JSON string
  createdAt: string;
  updatedAt: string;
  orders?: Order[];
  reservations?: Reservation[];
  conversations?: Conversation[];
  feedback?: Feedback[];
}

// ─── Extended / Composite Types ────────────────────────────────────────

export interface CartItem extends Omit<MenuItem, "category" | "orderItems" | "createdAt" | "updatedAt"> {
  quantity: number;
  notes: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole | "assistant";
  content: string;
  agentType: AgentType | null;
  timestamp: number;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  metadata?: Record<string, unknown>;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
}

// ─── API Types ────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error?: string;
  message?: string;
  pagination?: Pagination;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

// ─── Filter Types ─────────────────────────────────────────────────────

export interface MenuFilters {
  category?: string;
  dietary?: DietaryFilter[];
  spicyLevel?: SpicyLevel[];
  search?: string;
  isPopular?: boolean;
  isAvailable?: boolean;
  sortBy?: MenuSortOption;
  priceRange?: PriceRange;
}

export type DietaryFilter = "vegetarian" | "vegan" | "glutenFree";

export type MenuSortOption =
  | "name"
  | "price_asc"
  | "price_desc"
  | "popularity"
  | "spicy_level"
  | "preparation_time";

export interface PriceRange {
  min: number;
  max: number;
}

// ─── Request Types ────────────────────────────────────────────────────

export interface CreateOrderRequest {
  items: CreateOrderItemRequest[];
  type: OrderType;
  notes?: string;
  tableNumber?: string;
  userId?: string;
}

export interface CreateOrderItemRequest {
  menuItemId: string;
  quantity: number;
  notes?: string;
}

export interface CreateReservationRequest {
  customerName: string;
  customerPhone: string;
  customerEmail?: string;
  partySize: number;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  specialRequests?: string;
  occasion?: Occasion;
  userId?: string;
}

export interface SendChatMessageRequest {
  message: string;
  conversationId?: string;
  agentType?: AgentType;
  context?: Record<string, unknown>;
}

// ─── Helper: Parsed MenuItem ──────────────────────────────────────────
// For convenience when working with JSON fields

export interface ParsedMenuItem extends Omit<MenuItem, "ingredients" | "allergens" | "tags"> {
  ingredients: string[];
  allergens: string[];
  tags: string[];
}
