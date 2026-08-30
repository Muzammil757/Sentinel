The GOVERN verdict block: outcome, one-sentence headline, the reasons behind it, and the deciding authority. Top border carries the status colour; the rest stays neutral.

```jsx
<DecisionSummary outcome="blocked" headline="Execution blocked before any external call."
  policy="payout-v4" decidedAt="14:02:14 IST"
  reasons={[{label:'Trigger', value:'Amount exceeds vendor ceiling by 41%.'},{label:'Conflict', value:'risk-agent and settlement-agent disagreed on reversibility.'}]} />
```

`decidedBy` defaults to GOVERN and must never name a human reviewer.
