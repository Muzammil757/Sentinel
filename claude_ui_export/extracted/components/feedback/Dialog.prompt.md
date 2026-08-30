Modal for a single focused task (add annotation, request re-evaluation). Positions against the nearest positioned ancestor, so wrap screens in `position:relative`.

```jsx
<Dialog label="Human review" title="Add annotation" onClose={close}
  footer={<><Button onClick={close}>Cancel</Button><Button variant="primary">Record note</Button></>}>…</Dialog>
```
