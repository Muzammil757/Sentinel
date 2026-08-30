The single source of status colour in Sentinel: allowed, blocked, escalated, failed, conflict, pending, review.

```jsx
<StatusBadge status="blocked" />
<StatusBadge status="escalated" size="lg">Escalated to review</StatusBadge>
```

"review" means an annotation workflow is open — it never implies a reviewer can authorise execution.
