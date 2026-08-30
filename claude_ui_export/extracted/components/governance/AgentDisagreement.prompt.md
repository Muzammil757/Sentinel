Side-by-side agent positions when agents conflict. Never ranks the agents visually — GOVERN resolves, not the layout.

```jsx
<AgentDisagreement subject="Reversibility of the payout within SLA"
  positions={[{agent:'risk-agent v7', position:'Hold', basis:'Vendor ceiling breached.', confidence:'0.82'},
              {agent:'settlement-agent v3', position:'Release', basis:'Reversal window open for 6h.', confidence:'0.61'}]}
  resolvedBy="GOVERN · policy payout-v4" />
```
