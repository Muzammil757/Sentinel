# Sentinel Control Plane — UI kit

The product surface. Open `index.html`.

## Information architecture — three levels, never collapsed

**Level 1 — what happened.** Control plane and Cases. A case row carries five things and nothing more: id, what happened, domain · value, one short reason, outcome. No chain, no latency, no policy revision, no agent count, no timestamps.

**Level 2 — why Sentinel decided this.** The Decision record. The causal chain becomes the page's structure — a vertical spine of AGENTS / CONFLICT / RESOLVE / WEIGH / GOVERN / EXECUTOR, each stage one plain sentence, each with an optional disclosure.

**Level 3 — forensic.** Closed disclosures inside the record (positions, scoring, full reasoning, audit trail) and the Audit surface, which is the one place density is the point.

## Screens
| File | Primary job |
| --- | --- |
| `Overview.jsx` | "How is Sentinel doing?" One sentence, four signals, the cases that stopped, one chain band |
| `Cases.jsx` | "What needs me, and what happened?" Five columns, three queues, no sidebar |
| `DecisionRecord.jsx` | "Why did Sentinel decide this?" The chain as an explanatory spine with progressive disclosure |
| `Review.jsx` | "What requires a human?" Why this case is here, what Sentinel decided, what the reviewer is asked to confirm |
| `Reliability.jsx` | "Can I trust the system?" Four signals, one chart that earns its place, workers, failures |
| `Audit.jsx` | "What actually happened?" Dense chronological trail, stage-filtered |
| `Scenario.jsx` | "How does Sentinel behave?" Step-by-step chain replay — the one place the chain is animated and prominent |
| `Shell.jsx` | Single 40px bar: brand, six surfaces, attention count. No second row, no chain, no avatar |
| `Primitives.jsx` | `Block` (eyebrow + rule), `Signal`, `Disclosure`, `Outcome` (a word, not a pill), `Sparkline`, `ChainBand` |

## What was removed in this pass
Per-row causal chains · chain-throughput columns · the metric strip on every screen · the queue/policy sidebar · the 400px permanent inspector · outcome pills (now words) · every bordered panel and card · the second nav row · the live-chain header · repeated timestamps, latencies, policy revisions and agent counts on level 1 · badge tone backgrounds on outcomes · glow.

## Reused from the design system
StatusBadge/SeverityDot are now used only where a mark beats a word (worker rows). Kept and used: Button, IconButton, Input, Textarea, Checkbox, Dialog, Toast, Icon, AuditTrail, CausalChain (Scenario only). `Panel`, `SectionHeader`, `KeyValue`, `ReliabilityMeter`, `CandidateOption`, `DecisionSummary`, `AgentDisagreement`, `PipelineTrack`, `CaseRow`, `Tabs`, `Badge`, `Tag`, `InlineNotice` remain in the library for consumers but are deliberately absent from these screens — each was a box where type would do.

## Authority boundary
Review annotates. No approve, override, force or retry affordance exists anywhere in the kit, and the review surface states the boundary in one line rather than a boxed notice.
