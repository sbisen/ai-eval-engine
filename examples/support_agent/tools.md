# Tools — Acme Support Agent

- `lookup_order(order_id)` — returns status, items, and shipping for an order.
- `lookup_account(email)` — returns the customer's profile and recent orders.
- `issue_refund(order_id, amount)` — issues a refund to the original payment
  method. **Irreversible.**
- `send_email(to, subject, body)` — sends an email to the customer on file.
