# API Contract: Tax v2

## Base URL
`/api/v1/tax`

---

## 1. List Tax Jurisdictions
```
GET /api/v1/tax/jurisdictions
```
**Auth:** `require_tenant_context()`

**Response:**
```json
{
  "jurisdictions": [
    {
      "id": 1,
      "name": "إسرائيل",
      "code": "IL",
      "country_code": "IL",
      "region": null
    }
  ]
}
```

---

## 2. Create Tax Jurisdiction
```
POST /api/v1/tax/jurisdictions
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "name": "إسرائيل",
  "code": "IL",
  "country_code": "IL",
  "region": null
}
```

**Response:**
```json
{
  "jurisdiction": {
    "id": 1,
    "name": "إسرائيل",
    "code": "IL",
    "country_code": "IL",
    "region": null
  }
}
```

---

## 3. Set Tax Rate
```
POST /api/v1/tax/jurisdictions/{jurisdiction_id}/rates
```
**Auth:** `require_tenant_context()`

**Body:**
```json
{
  "rate": "17.00",
  "product_tax_code": null,
  "priority": 0
}
```

**Response:**
```json
{
  "rate": {
    "id": 1,
    "jurisdiction_id": 1,
    "rate": "17.00",
    "product_tax_code": null,
    "is_compound": false,
    "priority": 0
  }
}
```

---

## Service Notes
- Tax rates cascade: default rate applies unless `product_tax_code` override exists
- `is_compound` applies the rate on top of previously-calculated taxes
- `priority` determines order when multiple rates apply
