# API Contract: Draft Orders v2

## Base URL
`/api/v1/draft-orders`

---

## 1. List Draft Orders
```
GET /api/v1/draft-orders/
```
**Auth:** `require_tenant_context()`

**Response:**
```json
{
  "draft_orders": [
    {
      "id": 1,
      "draft_number": "DRA-20260702-001",
      "customer_email": "customer@example.com",
      "customer_first_name": "أحمد",
      "customer_last_name": "غنام",
      "status": "draft",
      "subtotal": "0.00",
      "tax_amount": "0.00",
      "shipping_cost": "0.00",
      "discount_amount": "0.00",
      "total": "0.00",
      "notes": "طلب خاص — تواصل معي",
      "send_email_invite": true,
      "converted_order_id": null,
      "completed_at": null
    }
  ]
}
```

---

## 2. Create Draft Order
```
POST /api/v1/draft-orders/
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "customer_email": "customer@example.com",
  "notes": "طلب خاص",
  "shipping_address": {},
  "send_email_invite": false
}
```

**Response:**
```json
{
  "draft_order": { ...draft object... }
}
```

---

## 3. Add Draft Order Item
```
POST /api/v1/draft-orders/{draft_id}/items
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "product_id": 1,
  "quantity": 2
}
```

**Response:**
```json
{
  "item": {
    "id": 1,
    "draft_order_id": 1,
    "product_id": 1,
    "product_name": "منتج تجريبي",
    "product_sku": "SKU-001",
    "unit_price": "50.00",
    "quantity": 2,
    "total_price": "100.00"
  }
}
```

---

## 4. Convert Draft to Order
```
POST /api/v1/draft-orders/{draft_id}/convert
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "customer_email": "customer@example.com"
}
```

**Response:**
```json
{
  "order": {
    "id": 123,
    "order_number": "ORD-20260702-123",
    "status": "draft",
    "customer_email": "customer@example.com"
  }
}
```

---

## Business Rules
- Draft orders are always scoped to the current tenant
- Conversion creates a real order and links it via `converted_order_id`
- Once converted, the draft status changes to `completed` and `completed_at` is set
- Email invites can be sent to customers to complete payment
