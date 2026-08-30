Primary console navigation: 236px, mono-uppercase section labels, tabular counts. `attention` turns a count amber.

```jsx
<SideNav value="cases" onSelect={setView} sections={[{label:'Operations',items:[{value:'cases',label:'Cases',icon:'inbox',count:4,attention:true}]}]} />
```
