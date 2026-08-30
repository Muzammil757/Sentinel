Shows where a case stopped and why, with no implementation detail. Stage names stay in the fixed vocabulary.

```jsx
<PipelineTrack stages={[
  {label:'Intake', state:'done', detail:'14:02:11'},
  {label:'Weigh', state:'done', detail:'3 candidates'},
  {label:'Govern', state:'blocked', detail:'policy payout-v4'},
  {label:'Execution', state:'skipped', detail:'not reached'},
  {label:'Review', state:'active', detail:'annotation open'},
]} />
```
