# API Contract: Subscriptions v2

## Base URL
`/api/v1/subscriptions`

---

## 1. List Subscription Plans
```
GET /api/v1/subscriptions/plans
```
**Auth:** `require_tenant_context()` (tenant header/subdomain)

**Response:**
```json
{
  "plans": [
    {
      "id": 1,
      "name": "الخطة الذهبية",
      "code": "gold",
      "billing_period_days": 30,
      "trial_period_days": 7,
      "price": "99.00",
      "currency": "ILS",
      "is_active": true,
      "max_products": 100,
      "max_orders_per_cycle": 500
    }
  ]
}
```

---

## 2. Create Subscription Plan
```
POST /api/v1/subscriptions/plans
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "name": "الخطة الذهبية",
  "code": "gold",
  "billing_period_days": 30,
  "price": "99.00",
  "trial_period_days": 7,
  "currency": "ILS",
  "max_products": 100,
  "max_orders_per_cycle": 500
}
```

**Response:**
```json
{
  "plan": { ...plan object... }
}
```

---

## 3. Subscribe Customer
```
POST /api/v1/subscriptions/subscribe
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "plan_id": 1,
  "customer_email": "customer@example.com"
}
```

**Response:**
```json
{
  "subscription": {
    "id": 1,
    "plan_id": 1,
    "customer_email": "customer@example.com",
    "status": "trialing",
    "current_period_start": "2026-07-02T12:00:00+00:00",
    "current_period_end": "2026-08-02T12:00:00+00:00",
    "trial_end": "2026-07-09T12:00:00+00:00"
  }
}
```

---

## 4. List Customer Subscriptions
```
GET /api/v1/subscriptions/subscriptions
```
**Auth:** `require_tenant_context()`

**Response:**
```json
{
  "subscriptions": [ ...subscription objects... ]
}
```

---

## 5. Cancel Subscription
```
POST /api/v1/subscriptions/subscriptions/{sub_id}/cancel
```
**Auth:** `require_tenant_context()`

**Response:**
```json
{
  "subscription": {
    "id": 1,
    "status": "cancelled",
    "cancelled_at": "2026-07-02T12:05:00+00:00"
  }
}
```

---

## 6. Create Digital Asset
```
POST /api/v1/subscriptions/digital-assets
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "product_id": 1,
  "file_url": "https://cdn.example.com/file.pdf",
  "file_name": "guide.pdf",
  "mime_type": "application/pdf",
  "max_downloads": 5
}
```

---

## 7. Create Download Token
```
POST /api/v1/subscriptions/digital-assets/{asset_id}/download
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "order_id": 123
}
```

---

## 8. Generate License Key
```
POST /api/v1/subscriptions/licenses
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "order_item_id": 1,
  "product_id": 1
}
```

**Response:**
```json
{
  "license": {
    "id": 1,
    "key": "LIC-A1B2C3D4E5F67890",
    "is_activated": false
  }
}
```

---

## Security Notes
- All endpoints enforce `tenant_id` isolation via service layer and PostgreSQL RLS
- Currency default: `ILS`
- `code` must be unique per tenant
