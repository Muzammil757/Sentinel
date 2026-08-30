Sentinel's recurring causal spine: AGENTS → CONFLICT → RESOLVE → WEIGH → GOVERN → EXECUTOR. Use it in the app header (system-wide), on every case row (per-case), and above a decision record.

```jsx
<CausalChain states={{ agents:'passed', conflict:'conflict', resolve:'passed', weigh:'passed', govern:'blocked', executor:'halted' }} detail="halted at GOVERN · 3.2s" />
<CausalChain size="sm" showLabels={false} states={{ agents:'passed', govern:'active' }} />
```

Link states: idle, clear, passed, active (glows), conflict, blocked, escalated, halted. Never reorder or rename the six links.
