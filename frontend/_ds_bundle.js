/* @ds-bundle: {"format":4,"namespace":"SentinelDesignSystem_8a81b0","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Tooltip","sourcePath":"components/core/Tooltip.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"InlineNotice","sourcePath":"components/feedback/InlineNotice.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Radio","sourcePath":"components/forms/Radio.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"Textarea","sourcePath":"components/forms/Textarea.jsx"},{"name":"AgentDisagreement","sourcePath":"components/governance/AgentDisagreement.jsx"},{"name":"AuditTrail","sourcePath":"components/governance/AuditTrail.jsx"},{"name":"CandidateOption","sourcePath":"components/governance/CandidateOption.jsx"},{"name":"CaseRow","sourcePath":"components/governance/CaseRow.jsx"},{"name":"DecisionSummary","sourcePath":"components/governance/DecisionSummary.jsx"},{"name":"PipelineTrack","sourcePath":"components/governance/PipelineTrack.jsx"},{"name":"SideNav","sourcePath":"components/navigation/SideNav.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"},{"name":"CausalChain","sourcePath":"components/pipeline/CausalChain.jsx"},{"name":"ReliabilityMeter","sourcePath":"components/status/ReliabilityMeter.jsx"},{"name":"SeverityDot","sourcePath":"components/status/SeverityDot.jsx"},{"name":"StatusBadge","sourcePath":"components/status/StatusBadge.jsx"},{"name":"KeyValue","sourcePath":"components/surfaces/KeyValue.jsx"},{"name":"Panel","sourcePath":"components/surfaces/Panel.jsx"},{"name":"SectionHeader","sourcePath":"components/surfaces/SectionHeader.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"8b6f5920a125","components/core/Button.jsx":"d99485e66c2a","components/core/Icon.jsx":"4c289c898a97","components/core/IconButton.jsx":"5d61efdafaff","components/core/Tag.jsx":"d0d8e3e1efca","components/core/Tooltip.jsx":"7539d2049620","components/feedback/Dialog.jsx":"6528b582d3b3","components/feedback/InlineNotice.jsx":"a19141143626","components/feedback/Toast.jsx":"8fb0c8e606b0","components/forms/Checkbox.jsx":"1b5f3b166421","components/forms/Input.jsx":"30dd1651c93e","components/forms/Radio.jsx":"0de310af12f7","components/forms/Select.jsx":"f0ce744f7c40","components/forms/Switch.jsx":"f3cc5923af2a","components/forms/Textarea.jsx":"be71086c01a3","components/governance/AgentDisagreement.jsx":"f75d318eaf68","components/governance/AuditTrail.jsx":"235c4f7cc882","components/governance/CandidateOption.jsx":"12b1dd03f598","components/governance/CaseRow.jsx":"6d606660e80f","components/governance/DecisionSummary.jsx":"b42e13116117","components/governance/PipelineTrack.jsx":"d0e305087982","components/navigation/SideNav.jsx":"e085b44aa6f7","components/navigation/Tabs.jsx":"8aaf18031d42","components/pipeline/CausalChain.jsx":"af3161ba33cc","components/status/ReliabilityMeter.jsx":"543ce9011fb3","components/status/SeverityDot.jsx":"a804a51a0814","components/status/StatusBadge.jsx":"990ed0c41134","components/surfaces/KeyValue.jsx":"becae264d4ca","components/surfaces/Panel.jsx":"bde786391f11","components/surfaces/SectionHeader.jsx":"ce78c9092549","ui_kits/control_plane/Audit.jsx":"59d58b59abc5","ui_kits/control_plane/Cases.jsx":"9bd5cb4f8d1c","ui_kits/control_plane/Data.jsx":"679a83f617f5","ui_kits/control_plane/DecisionRecord.jsx":"bfd0c3380670","ui_kits/control_plane/Overview.jsx":"bbfea10f6b45","ui_kits/control_plane/Primitives.jsx":"61f9f538c5e2","ui_kits/control_plane/Reliability.jsx":"df62bb0dd691","ui_kits/control_plane/Review.jsx":"9210925648c5","ui_kits/control_plane/Scenario.jsx":"9a102d0a5b77","ui_kits/control_plane/Shell.jsx":"2e1e2c69dda7"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.SentinelDesignSystem_8a81b0 = window.SentinelDesignSystem_8a81b0 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TONES = {
  neutral: {
    bg: 'var(--bg-inset)',
    fg: 'var(--text-secondary)',
    bd: 'var(--border-subtle)'
  },
  accent: {
    bg: 'var(--blue-50)',
    fg: 'var(--blue-700)',
    bd: 'var(--blue-100)'
  },
  allowed: {
    bg: 'var(--status-allowed-bg)',
    fg: 'var(--status-allowed-fg)',
    bd: 'transparent'
  },
  escalated: {
    bg: 'var(--status-escalated-bg)',
    fg: 'var(--status-escalated-fg)',
    bd: 'transparent'
  },
  blocked: {
    bg: 'var(--status-blocked-bg)',
    fg: 'var(--status-blocked-fg)',
    bd: 'transparent'
  },
  conflict: {
    bg: 'var(--status-conflict-bg)',
    fg: 'var(--status-conflict-fg)',
    bd: 'transparent'
  }
};
function Badge({
  children,
  tone = 'neutral',
  mono = false,
  style,
  ...rest
}) {
  const t = TONES[tone] || TONES.neutral;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      height: 18,
      padding: '0 6px',
      borderRadius: 'var(--radius-3)',
      background: t.bg,
      color: t.fg,
      border: `1px solid ${t.bd}`,
      font: mono ? 'var(--type-label)' : 'var(--fw-medium) var(--fs-11)/1 var(--font-sans)',
      letterSpacing: mono ? 'var(--ls-label)' : 'var(--ls-caps)',
      textTransform: mono ? 'uppercase' : 'none',
      whiteSpace: 'nowrap',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CDN = 'https://unpkg.com/lucide-static@0.469.0/icons/';

/* Lucide (1.5px stroke) is the substituted icon set for Sentinel — glyphs are loaded as
   CSS masks so they inherit currentColor and stay crisp at 14–20px. */
function Icon({
  name,
  size = 16,
  strokeAlign = 'center',
  style,
  className,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("span", _extends({
    role: "img",
    "aria-hidden": "true",
    "data-icon": name,
    className: className,
    style: {
      display: 'inline-block',
      width: size,
      height: size,
      flex: '0 0 auto',
      backgroundColor: 'currentColor',
      WebkitMask: `url(${CDN}${name}.svg) ${strokeAlign} / contain no-repeat`,
      mask: `url(${CDN}${name}.svg) ${strokeAlign} / contain no-repeat`,
      ...style
    }
  }, rest));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const SIZES = {
  sm: {
    height: 26,
    padding: '0 8px',
    font: 'var(--fw-medium) var(--fs-12)/1 var(--font-sans)',
    gap: 6,
    icon: 13
  },
  md: {
    height: 'var(--control-height)',
    padding: '0 12px',
    font: 'var(--fw-medium) var(--fs-13)/1 var(--font-sans)',
    gap: 6,
    icon: 14
  },
  lg: {
    height: 'var(--control-height-lg)',
    padding: '0 16px',
    font: 'var(--fw-medium) var(--fs-14)/1 var(--font-sans)',
    gap: 8,
    icon: 16
  }
};
const VARIANTS = {
  primary: {
    rest: {
      background: 'var(--accent)',
      color: 'var(--text-inverse)',
      border: '1px solid var(--accent)'
    },
    hover: {
      background: 'var(--accent-hover)',
      border: '1px solid var(--accent-hover)'
    },
    press: {
      background: 'var(--accent-press)',
      border: '1px solid var(--accent-press)'
    }
  },
  secondary: {
    rest: {
      background: 'var(--bg-surface)',
      color: 'var(--text-primary)',
      border: '1px solid var(--border-strong)',
      boxShadow: 'var(--shadow-1)'
    },
    hover: {
      background: 'var(--bg-hover)',
      border: '1px solid var(--ink-300)'
    },
    press: {
      background: 'var(--bg-active)'
    }
  },
  ghost: {
    rest: {
      background: 'transparent',
      color: 'var(--text-secondary)',
      border: '1px solid transparent'
    },
    hover: {
      background: 'var(--bg-hover)',
      color: 'var(--text-primary)'
    },
    press: {
      background: 'var(--bg-active)'
    }
  },
  danger: {
    rest: {
      background: 'var(--bg-surface)',
      color: 'var(--red-700)',
      border: '1px solid var(--red-100)'
    },
    hover: {
      background: 'var(--red-100)'
    },
    press: {
      background: 'var(--red-100)',
      color: 'var(--red-700)'
    }
  }
};
function Button({
  children,
  variant = 'secondary',
  size = 'md',
  icon,
  trailingIcon,
  disabled = false,
  loading = false,
  fullWidth = false,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);
  const s = SIZES[size] || SIZES.md;
  const v = VARIANTS[variant] || VARIANTS.secondary;
  const state = disabled ? {} : press ? {
    ...v.hover,
    ...v.press
  } : hover ? v.hover : {};
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    disabled: disabled || loading,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setPress(false);
    },
    onMouseDown: () => setPress(true),
    onMouseUp: () => setPress(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: fullWidth ? '100%' : 'auto',
      height: s.height,
      padding: s.padding,
      gap: s.gap,
      font: s.font,
      letterSpacing: 'var(--ls-body)',
      borderRadius: 'var(--radius-4)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.45 : 1,
      transition: 'var(--transition-control)',
      whiteSpace: 'nowrap',
      ...v.rest,
      ...state,
      ...style
    }
  }, rest), loading ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "loader",
    size: s.icon
  }) : icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: s.icon
  }) : null, children, trailingIcon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: trailingIcon,
    size: s.icon
  }) : null);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const BOX = {
  sm: 24,
  md: 30,
  lg: 36
};
const GLYPH = {
  sm: 14,
  md: 16,
  lg: 18
};
function IconButton({
  icon,
  size = 'md',
  variant = 'ghost',
  active = false,
  disabled = false,
  label,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const box = BOX[size] || BOX.md;
  const bordered = variant === 'outline';
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    "aria-label": label,
    title: label,
    disabled: disabled,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: box,
      height: box,
      borderRadius: 'var(--radius-4)',
      border: bordered ? '1px solid var(--border-strong)' : '1px solid transparent',
      background: active ? 'var(--bg-active)' : hover && !disabled ? 'var(--bg-hover)' : bordered ? 'var(--bg-surface)' : 'transparent',
      color: active ? 'var(--text-primary)' : hover && !disabled ? 'var(--text-primary)' : 'var(--text-secondary)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.4 : 1,
      transition: 'var(--transition-control)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: GLYPH[size] || 16
  }));
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Tag({
  children,
  onRemove,
  icon,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("span", _extends({
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      height: 22,
      padding: '0 7px',
      borderRadius: 'var(--radius-3)',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-subtle)',
      color: 'var(--text-secondary)',
      font: 'var(--type-mono)',
      letterSpacing: 'var(--ls-mono)',
      transition: 'var(--transition-control)',
      ...(hover ? {
        borderColor: 'var(--border-strong)',
        color: 'var(--text-primary)'
      } : null),
      ...style
    }
  }, rest), icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 12
  }) : null, children, onRemove ? /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: onRemove,
    "aria-label": "Remove",
    style: {
      display: 'inline-flex',
      border: 0,
      background: 'none',
      padding: 0,
      marginLeft: 1,
      cursor: 'pointer',
      color: 'var(--text-tertiary)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 11
  })) : null);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/core/Tooltip.jsx
try { (() => {
function Tooltip({
  label,
  side = 'top',
  children,
  style
}) {
  const [open, setOpen] = React.useState(false);
  const pos = {
    top: {
      bottom: '100%',
      left: '50%',
      transform: 'translate(-50%,-6px)'
    },
    bottom: {
      top: '100%',
      left: '50%',
      transform: 'translate(-50%,6px)'
    },
    right: {
      left: '100%',
      top: '50%',
      transform: 'translate(6px,-50%)'
    },
    left: {
      right: '100%',
      top: '50%',
      transform: 'translate(-6px,-50%)'
    }
  }[side];
  return /*#__PURE__*/React.createElement("span", {
    onMouseEnter: () => setOpen(true),
    onMouseLeave: () => setOpen(false),
    onFocus: () => setOpen(true),
    onBlur: () => setOpen(false),
    style: {
      position: 'relative',
      display: 'inline-flex',
      ...style
    }
  }, children, /*#__PURE__*/React.createElement("span", {
    role: "tooltip",
    style: {
      position: 'absolute',
      ...pos,
      zIndex: 40,
      pointerEvents: 'none',
      padding: '4px 7px',
      borderRadius: 'var(--radius-3)',
      background: 'var(--ink-900)',
      color: 'var(--text-inverse)',
      font: 'var(--fw-regular) var(--fs-12)/1.35 var(--font-sans)',
      maxWidth: 240,
      whiteSpace: 'nowrap',
      boxShadow: 'var(--shadow-2)',
      opacity: open ? 1 : 0,
      transition: `opacity var(--dur-fast) var(--ease-standard)`
    }
  }, label));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
function Dialog({
  open = true,
  title,
  label,
  description,
  footer,
  width = 480,
  onClose,
  children,
  style
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      zIndex: 60,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--overlay-scrim)',
      backdropFilter: 'var(--blur-scrim)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    role: "dialog",
    "aria-modal": "true",
    style: {
      width,
      maxWidth: '92%',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-6)',
      boxShadow: 'var(--shadow-popover)',
      display: 'flex',
      flexDirection: 'column',
      ...style
    }
  }, /*#__PURE__*/React.createElement("header", {
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: 12,
      padding: '14px 12px 12px 16px',
      borderBottom: '1px solid var(--border-hairline)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      gap: 3
    }
  }, label ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)'
    }
  }, label) : null, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-heading)',
      letterSpacing: 'var(--ls-heading)'
    }
  }, title), description ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--text-secondary)',
      textWrap: 'pretty'
    }
  }, description) : null), onClose ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    size: "sm",
    label: "Close",
    onClick: onClose
  }) : null), children ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 16
    }
  }, children) : null, footer ? /*#__PURE__*/React.createElement("footer", {
    style: {
      display: 'flex',
      justifyContent: 'flex-end',
      gap: 8,
      padding: '12px 16px',
      borderTop: '1px solid var(--border-hairline)',
      background: 'var(--bg-inset)',
      borderRadius: '0 0 var(--radius-6) var(--radius-6)'
    }
  }, footer) : null));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/feedback/InlineNotice.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TONES = {
  info: {
    fg: 'var(--blue-700)',
    bg: 'var(--blue-50)',
    bd: 'var(--blue-100)',
    icon: 'info'
  },
  attention: {
    fg: 'var(--status-escalated-fg)',
    bg: 'var(--status-escalated-bg)',
    bd: 'transparent',
    icon: 'triangle-alert'
  },
  blocked: {
    fg: 'var(--status-blocked-fg)',
    bg: 'var(--status-blocked-bg)',
    bd: 'transparent',
    icon: 'shield-x'
  },
  neutral: {
    fg: 'var(--text-secondary)',
    bg: 'var(--bg-inset)',
    bd: 'var(--border-subtle)',
    icon: 'lock'
  }
};
function InlineNotice({
  tone = 'info',
  title,
  children,
  actions,
  icon,
  style,
  ...rest
}) {
  const t = TONES[tone] || TONES.info;
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      gap: 9,
      padding: '10px 12px',
      borderRadius: 'var(--radius-4)',
      background: t.bg,
      border: `1px solid ${t.bd}`,
      color: t.fg,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon || t.icon,
    size: 15,
    style: {
      marginTop: 1
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      minWidth: 0,
      flex: 1
    }
  }, title ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-subheading)'
    }
  }, title) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'inherit',
      opacity: 0.92,
      textWrap: 'pretty'
    }
  }, children), actions ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 6,
      marginTop: 4
    }
  }, actions) : null));
}
Object.assign(__ds_scope, { InlineNotice });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/InlineNotice.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Toast({
  tone = 'neutral',
  title,
  detail,
  onDismiss,
  style,
  ...rest
}) {
  const accent = {
    neutral: 'var(--ink-300)',
    allowed: 'var(--status-allowed-dot)',
    blocked: 'var(--status-blocked-dot)',
    escalated: 'var(--status-escalated-dot)'
  }[tone];
  const icon = {
    neutral: 'info',
    allowed: 'check',
    blocked: 'shield-x',
    escalated: 'arrow-up-right'
  }[tone];
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: 9,
      minWidth: 300,
      maxWidth: 420,
      padding: '10px 10px 10px 12px',
      background: 'var(--bg-console)',
      color: 'var(--text-inverse)',
      border: '1px solid var(--border-console)',
      borderRadius: 'var(--radius-4)',
      boxShadow: 'var(--shadow-popover)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 14,
    style: {
      color: accent,
      marginTop: 2
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0,
      display: 'flex',
      flexDirection: 'column',
      gap: 2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--fw-medium) var(--fs-13)/1.3 var(--font-sans)'
    }
  }, title), detail ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-inverse-secondary)'
    }
  }, detail) : null), onDismiss ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    size: "sm",
    label: "Dismiss",
    onClick: onDismiss,
    style: {
      color: 'var(--text-inverse-secondary)'
    }
  }) : null);
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function Checkbox({
  label,
  description,
  checked,
  indeterminate = false,
  disabled = false,
  onChange,
  style
}) {
  const on = checked || indeterminate;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      gap: 8,
      alignItems: description ? 'flex-start' : 'center',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.45 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: !!checked,
    disabled: disabled,
    onChange: onChange,
    style: {
      position: 'absolute',
      opacity: 0,
      width: 0,
      height: 0
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 15,
      height: 15,
      flex: '0 0 auto',
      marginTop: description ? 2 : 0,
      borderRadius: 'var(--radius-3)',
      border: `1px solid ${on ? 'var(--accent)' : 'var(--border-emphasis)'}`,
      background: on ? 'var(--accent)' : 'var(--bg-surface)',
      color: 'var(--text-inverse)',
      transition: 'var(--transition-control)'
    }
  }, indeterminate ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "minus",
    size: 11
  }) : checked ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "check",
    size: 11
  }) : null), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 1
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)'
    }
  }, label), description ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-caption)',
      color: 'var(--text-secondary)'
    }
  }, description) : null));
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Input({
  label,
  hint,
  error,
  icon,
  mono = false,
  size = 'md',
  style,
  wrapperStyle,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const h = size === 'lg' ? 'var(--control-height-lg)' : 'var(--control-height)';
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      ...wrapperStyle
    }
  }, label ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)'
    }
  }, label) : null, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 7,
      height: h,
      padding: '0 9px',
      background: 'var(--bg-surface)',
      borderRadius: 'var(--radius-4)',
      border: `1px solid ${error ? 'var(--red-600)' : focus ? 'var(--accent)' : 'var(--border-strong)'}`,
      boxShadow: focus ? `0 0 0 3px var(--focus-ring)` : 'none',
      transition: 'var(--transition-control)',
      color: 'var(--text-tertiary)'
    }
  }, icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 14
  }) : null, /*#__PURE__*/React.createElement("input", _extends({
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      flex: 1,
      minWidth: 0,
      border: 0,
      outline: 'none',
      background: 'none',
      font: mono ? 'var(--type-mono)' : 'var(--type-body-sm)',
      letterSpacing: mono ? 'var(--ls-mono)' : 'var(--ls-body)',
      color: 'var(--text-primary)',
      ...style
    }
  }, rest))), error || hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-caption)',
      color: error ? 'var(--red-700)' : 'var(--text-tertiary)'
    }
  }, error || hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Radio.jsx
try { (() => {
function Radio({
  label,
  description,
  checked,
  disabled = false,
  name,
  value,
  onChange,
  style
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      gap: 8,
      alignItems: description ? 'flex-start' : 'center',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.45 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "radio",
    name: name,
    value: value,
    checked: !!checked,
    disabled: disabled,
    onChange: onChange,
    style: {
      position: 'absolute',
      opacity: 0,
      width: 0,
      height: 0
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 15,
      height: 15,
      flex: '0 0 auto',
      marginTop: description ? 2 : 0,
      borderRadius: 'var(--radius-pill)',
      border: `1px solid ${checked ? 'var(--accent)' : 'var(--border-emphasis)'}`,
      background: 'var(--bg-surface)',
      transition: 'var(--transition-control)'
    }
  }, checked ? /*#__PURE__*/React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: 'var(--radius-pill)',
      background: 'var(--accent)'
    }
  }) : null), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 1
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)'
    }
  }, label), description ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-caption)',
      color: 'var(--text-secondary)'
    }
  }, description) : null));
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Radio.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Select({
  label,
  options = [],
  hint,
  size = 'md',
  style,
  wrapperStyle,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      ...wrapperStyle
    }
  }, label ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)'
    }
  }, label) : null, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      height: size === 'lg' ? 'var(--control-height-lg)' : 'var(--control-height)',
      background: 'var(--bg-surface)',
      borderRadius: 'var(--radius-4)',
      border: `1px solid ${focus ? 'var(--accent)' : 'var(--border-strong)'}`,
      boxShadow: focus ? '0 0 0 3px var(--focus-ring)' : 'var(--shadow-1)',
      transition: 'var(--transition-control)'
    }
  }, /*#__PURE__*/React.createElement("select", _extends({
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      appearance: 'none',
      WebkitAppearance: 'none',
      border: 0,
      outline: 'none',
      background: 'none',
      padding: '0 26px 0 9px',
      width: '100%',
      height: '100%',
      font: 'var(--type-body-sm)',
      color: 'var(--text-primary)',
      cursor: 'pointer',
      ...style
    }
  }, rest), options.map(o => {
    const v = typeof o === 'string' ? o : o.value;
    const l = typeof o === 'string' ? o : o.label;
    return /*#__PURE__*/React.createElement("option", {
      key: v,
      value: v
    }, l);
  })), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 13,
    style: {
      position: 'absolute',
      right: 8,
      color: 'var(--text-tertiary)',
      pointerEvents: 'none'
    }
  })), hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-caption)',
      color: 'var(--text-tertiary)'
    }
  }, hint) : null);
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function Switch({
  checked = false,
  disabled = false,
  label,
  onChange,
  style
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.45 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    role: "switch",
    "aria-checked": checked,
    disabled: disabled,
    onClick: onChange,
    style: {
      position: 'relative',
      width: 30,
      height: 17,
      flex: '0 0 auto',
      padding: 0,
      borderRadius: 'var(--radius-pill)',
      cursor: 'inherit',
      border: `1px solid ${checked ? 'var(--accent)' : 'var(--border-emphasis)'}`,
      background: checked ? 'var(--accent)' : 'var(--bg-inset)',
      transition: 'var(--transition-control)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: 2,
      left: checked ? 15 : 2,
      width: 11,
      height: 11,
      borderRadius: 'var(--radius-pill)',
      background: 'var(--white)',
      boxShadow: '0 1px 1px rgba(11,14,19,.2)',
      transition: `left var(--dur-fast) var(--ease-standard)`
    }
  })), label ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)'
    }
  }, label) : null);
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/forms/Textarea.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Textarea({
  label,
  hint,
  rows = 3,
  counter,
  value,
  style,
  wrapperStyle,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      ...wrapperStyle
    }
  }, label ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)'
    }
  }, label) : null, /*#__PURE__*/React.createElement("textarea", _extends({
    rows: rows,
    value: value,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      resize: 'vertical',
      padding: '8px 9px',
      background: 'var(--bg-surface)',
      borderRadius: 'var(--radius-4)',
      border: `1px solid ${focus ? 'var(--accent)' : 'var(--border-strong)'}`,
      boxShadow: focus ? '0 0 0 3px var(--focus-ring)' : 'none',
      outline: 'none',
      font: 'var(--type-body-sm)',
      color: 'var(--text-primary)',
      transition: 'var(--transition-control)',
      ...style
    }
  }, rest)), hint || counter ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      font: 'var(--type-caption)',
      color: 'var(--text-tertiary)'
    }
  }, /*#__PURE__*/React.createElement("span", null, hint), counter ? /*#__PURE__*/React.createElement("span", {
    "data-numeric": true
  }, counter) : null) : null);
}
Object.assign(__ds_scope, { Textarea });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Textarea.jsx", error: String((e && e.message) || e) }); }

// components/governance/AgentDisagreement.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function AgentDisagreement({
  positions = [],
  subject,
  resolvedBy,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      ...style
    }
  }, rest), subject ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 7,
      font: 'var(--type-body-sm)',
      color: 'var(--text-secondary)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "git-compare",
    size: 14,
    style: {
      color: 'var(--status-conflict-dot)'
    }
  }), /*#__PURE__*/React.createElement("span", null, subject)) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: `repeat(${Math.max(positions.length, 1)}, minmax(0,1fr))`,
      gap: 1,
      background: 'var(--border-subtle)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-4)',
      overflow: 'hidden'
    }
  }, positions.map((p, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      background: 'var(--bg-surface)',
      padding: '10px 12px',
      display: 'flex',
      flexDirection: 'column',
      gap: 5,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--status-conflict-fg)'
    }
  }, p.agent), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--fw-medium) var(--fs-13)/1.35 var(--font-sans)',
      textWrap: 'pretty'
    }
  }, p.position), p.basis ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--text-secondary)',
      textWrap: 'pretty'
    }
  }, p.basis) : null, p.confidence != null ? /*#__PURE__*/React.createElement("span", {
    "data-numeric": true,
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)'
    }
  }, "confidence ", p.confidence) : null))), resolvedBy ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)'
    }
  }, "resolved by ", resolvedBy) : null);
}
Object.assign(__ds_scope, { AgentDisagreement });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/governance/AgentDisagreement.jsx", error: String((e && e.message) || e) }); }

// components/governance/AuditTrail.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const ACTOR_COLOR = {
  system: 'var(--text-inverse-secondary)',
  govern: '#7FA6F0',
  agent: '#B3A2E0',
  execution: '#7FCFA8',
  reviewer: '#E3C07B'
};
function AuditTrail({
  entries = [],
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("ol", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 0,
      margin: 0,
      padding: 0,
      listStyle: 'none',
      background: 'var(--bg-console)',
      color: 'var(--text-inverse)',
      borderRadius: 'var(--radius-4)',
      border: '1px solid var(--border-console)',
      font: 'var(--type-mono)',
      overflow: 'hidden',
      ...style
    }
  }, rest), entries.map((e, i) => /*#__PURE__*/React.createElement("li", {
    key: i,
    style: {
      display: 'grid',
      gridTemplateColumns: '92px 84px minmax(0,1fr)',
      gap: 12,
      padding: '7px 12px',
      borderBottom: i === entries.length - 1 ? 0 : '1px solid rgba(255,255,255,.06)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    "data-numeric": true,
    style: {
      color: 'var(--text-inverse-secondary)'
    }
  }, e.time), /*#__PURE__*/React.createElement("span", {
    style: {
      color: ACTOR_COLOR[e.actorKind] || 'var(--text-inverse-secondary)',
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-label)',
      fontSize: 'var(--fs-11)'
    }
  }, e.actor), /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'rgba(255,255,255,.88)',
      textWrap: 'pretty'
    }
  }, e.message, e.detail ? /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-inverse-secondary)'
    }
  }, '  ', e.detail) : null))));
}
Object.assign(__ds_scope, { AuditTrail });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/governance/AuditTrail.jsx", error: String((e && e.message) || e) }); }

// components/governance/CandidateOption.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function CandidateOption({
  name,
  proposedBy,
  score,
  verdict = 'considered',
  rationale,
  selected = false,
  rank,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const v = {
    chosen: {
      fg: 'var(--status-allowed-fg)',
      label: 'Chosen',
      icon: 'check'
    },
    rejected: {
      fg: 'var(--status-blocked-fg)',
      label: 'Rejected',
      icon: 'x'
    },
    considered: {
      fg: 'var(--text-tertiary)',
      label: 'Considered',
      icon: 'minus'
    }
  }[verdict];
  return /*#__PURE__*/React.createElement("div", _extends({
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: 'grid',
      gridTemplateColumns: '20px minmax(0,1fr) 60px 92px',
      gap: 12,
      alignItems: 'start',
      padding: '10px 12px',
      borderBottom: '1px solid var(--border-hairline)',
      background: selected ? 'var(--bg-selected)' : hover ? 'var(--bg-hover)' : 'transparent',
      transition: 'var(--transition-control)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    "data-numeric": true,
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)',
      paddingTop: 1
    }
  }, rank), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 3,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--fw-medium) var(--fs-13)/1.3 var(--font-sans)'
    }
  }, name), rationale ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--text-secondary)',
      textWrap: 'pretty'
    }
  }, rationale) : null, proposedBy ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)'
    }
  }, "proposed by ", proposedBy) : null), /*#__PURE__*/React.createElement("span", {
    "data-numeric": true,
    style: {
      font: 'var(--fw-medium) var(--fs-13)/1.3 var(--font-mono)',
      textAlign: 'right'
    }
  }, score), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'flex-end',
      gap: 5,
      font: 'var(--fw-medium) var(--fs-11)/1.3 var(--font-sans)',
      letterSpacing: 'var(--ls-caps)',
      textTransform: 'uppercase',
      color: v.fg
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: v.icon,
    size: 12
  }), v.label));
}
Object.assign(__ds_scope, { CandidateOption });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/governance/CandidateOption.jsx", error: String((e && e.message) || e) }); }

// components/governance/PipelineTrack.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const STATE = {
  done: {
    fg: 'var(--text-primary)',
    mark: 'var(--status-allowed-dot)',
    icon: 'check'
  },
  active: {
    fg: 'var(--text-primary)',
    mark: 'var(--accent)',
    icon: 'dot'
  },
  blocked: {
    fg: 'var(--status-blocked-fg)',
    mark: 'var(--status-blocked-dot)',
    icon: 'x'
  },
  halted: {
    fg: 'var(--status-escalated-fg)',
    mark: 'var(--status-escalated-dot)',
    icon: 'pause'
  },
  skipped: {
    fg: 'var(--text-tertiary)',
    mark: 'var(--ink-200)',
    icon: 'minus'
  },
  pending: {
    fg: 'var(--text-tertiary)',
    mark: 'var(--ink-200)',
    icon: 'dot'
  }
};
function PipelineTrack({
  stages = [],
  orientation = 'horizontal',
  style,
  ...rest
}) {
  const vertical = orientation === 'vertical';
  return /*#__PURE__*/React.createElement("ol", _extends({
    style: {
      display: 'flex',
      flexDirection: vertical ? 'column' : 'row',
      alignItems: vertical ? 'stretch' : 'stretch',
      gap: 0,
      margin: 0,
      padding: 0,
      listStyle: 'none',
      minWidth: 0,
      ...style
    }
  }, rest), stages.map((s, i) => {
    const st = STATE[s.state] || STATE.pending;
    const last = i === stages.length - 1;
    return /*#__PURE__*/React.createElement("li", {
      key: s.label,
      style: {
        display: 'flex',
        flexDirection: vertical ? 'row' : 'column',
        gap: vertical ? 10 : 0,
        flex: vertical ? 'none' : 1,
        minWidth: 0,
        paddingBottom: vertical && !last ? 14 : 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: vertical ? 'column' : 'row',
        alignItems: 'center',
        gap: 0,
        flex: '0 0 auto'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 16,
        height: 16,
        borderRadius: 'var(--radius-pill)',
        flex: '0 0 auto',
        background: s.state === 'pending' || s.state === 'skipped' ? 'transparent' : st.mark,
        border: `1px solid ${s.state === 'pending' || s.state === 'skipped' ? 'var(--border-strong)' : st.mark}`,
        color: 'var(--white)'
      }
    }, s.state === 'done' ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: "check",
      size: 10
    }) : s.state === 'blocked' ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: "x",
      size: 10
    }) : s.state === 'active' ? /*#__PURE__*/React.createElement("span", {
      style: {
        width: 5,
        height: 5,
        borderRadius: 99,
        background: '#fff'
      }
    }) : null), !last ? /*#__PURE__*/React.createElement("span", {
      style: {
        flex: vertical ? '0 0 auto' : 1,
        alignSelf: 'stretch',
        width: vertical ? 1 : 'auto',
        minHeight: vertical ? 18 : 0,
        height: vertical ? '100%' : 1,
        margin: vertical ? '4px 0 0 7px' : '0 6px',
        background: 'var(--border-strong)'
      }
    }) : null), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        paddingTop: vertical ? 0 : 8,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: st.fg
      }
    }, s.label), s.detail ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, s.detail) : null));
  }));
}
Object.assign(__ds_scope, { PipelineTrack });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/governance/PipelineTrack.jsx", error: String((e && e.message) || e) }); }

// components/navigation/SideNav.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Item({
  item,
  active,
  onSelect
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => onSelect && onSelect(item.value),
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 9,
      width: '100%',
      height: 30,
      padding: '0 8px',
      border: 0,
      borderRadius: 'var(--radius-4)',
      cursor: 'pointer',
      background: active ? 'var(--bg-active)' : hover ? 'var(--bg-hover)' : 'transparent',
      color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
      font: `${active ? 'var(--fw-medium)' : 'var(--fw-regular)'} var(--fs-13)/1 var(--font-sans)`,
      transition: 'var(--transition-control)',
      textAlign: 'left'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: item.icon,
    size: 15,
    style: {
      color: active ? 'var(--text-primary)' : 'var(--text-tertiary)'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      minWidth: 0,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, item.label), item.count != null ? /*#__PURE__*/React.createElement("span", {
    "data-numeric": true,
    style: {
      font: 'var(--type-mono)',
      fontSize: 'var(--fs-11)',
      color: item.attention ? 'var(--status-escalated-fg)' : 'var(--text-tertiary)'
    }
  }, item.count) : null);
}
function SideNav({
  sections = [],
  value,
  onSelect,
  header,
  footer,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("nav", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      width: 'var(--sidebar-width)',
      flex: '0 0 auto',
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-subtle)',
      ...style
    }
  }, rest), header ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '12px 12px 8px'
    }
  }, header) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflow: 'auto',
      padding: '4px 8px 12px',
      display: 'flex',
      flexDirection: 'column',
      gap: 14
    }
  }, sections.map((sec, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 1
    }
  }, sec.label ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '6px 8px 4px',
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)'
    }
  }, sec.label) : null, sec.items.map(it => /*#__PURE__*/React.createElement(Item, {
    key: it.value,
    item: it,
    active: value === it.value,
    onSelect: onSelect
  }))))), footer ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 12,
      borderTop: '1px solid var(--border-hairline)'
    }
  }, footer) : null);
}
Object.assign(__ds_scope, { SideNav });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/SideNav.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Tabs({
  items = [],
  value,
  onChange,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    role: "tablist",
    style: {
      display: 'flex',
      alignItems: 'stretch',
      gap: 2,
      borderBottom: '1px solid var(--border-subtle)',
      ...style
    }
  }, rest), items.map(it => {
    const id = typeof it === 'string' ? it : it.value;
    const label = typeof it === 'string' ? it : it.label;
    const count = typeof it === 'string' ? null : it.count;
    const active = value === id;
    return /*#__PURE__*/React.createElement("button", {
      key: id,
      role: "tab",
      "aria-selected": active,
      onClick: () => onChange && onChange(id),
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        height: 34,
        padding: '0 10px',
        border: 0,
        background: 'none',
        cursor: 'pointer',
        font: `var(--fw-medium) var(--fs-13)/1 var(--font-sans)`,
        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
        boxShadow: active ? 'inset 0 -2px 0 var(--ink-900)' : 'none',
        transition: 'var(--transition-control)'
      }
    }, label, count != null ? /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        fontSize: 'var(--fs-11)',
        color: active ? 'var(--text-secondary)' : 'var(--text-tertiary)'
      }
    }, count) : null);
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/pipeline/CausalChain.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const LINKS = ['Agents', 'Conflict', 'Resolve', 'Weigh', 'Govern', 'Executor'];
const TONE = {
  clear: {
    fg: 'var(--text-secondary)',
    mark: 'var(--border-emphasis)',
    fill: 'transparent'
  },
  passed: {
    fg: 'var(--text-primary)',
    mark: 'var(--status-allowed-dot)',
    fill: 'var(--status-allowed-dot)'
  },
  active: {
    fg: 'var(--text-primary)',
    mark: 'var(--accent)',
    fill: 'var(--accent)'
  },
  conflict: {
    fg: 'var(--status-conflict-fg)',
    mark: 'var(--status-conflict-dot)',
    fill: 'var(--status-conflict-dot)'
  },
  blocked: {
    fg: 'var(--status-blocked-fg)',
    mark: 'var(--status-blocked-dot)',
    fill: 'var(--status-blocked-dot)'
  },
  escalated: {
    fg: 'var(--status-escalated-fg)',
    mark: 'var(--status-escalated-dot)',
    fill: 'var(--status-escalated-dot)'
  },
  halted: {
    fg: 'var(--text-tertiary)',
    mark: 'var(--border-strong)',
    fill: 'transparent'
  },
  idle: {
    fg: 'var(--text-tertiary)',
    mark: 'var(--border-strong)',
    fill: 'transparent'
  }
};
function CausalChain({
  states = {},
  size = 'md',
  showLabels = true,
  detail,
  style,
  ...rest
}) {
  const compact = size === 'sm';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: compact ? 6 : 10,
      minWidth: 0,
      ...style
    }
  }, rest), LINKS.map((link, i) => {
    const key = link.toLowerCase();
    const state = states[key] || 'idle';
    const t = TONE[state] || TONE.idle;
    const live = state === 'active';
    return /*#__PURE__*/React.createElement(React.Fragment, {
      key: link
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: compact ? 4 : 6,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: compact ? 5 : 7,
        height: compact ? 5 : 7,
        flex: '0 0 auto',
        borderRadius: 'var(--radius-pill)',
        background: t.fill,
        border: t.fill === 'transparent' ? `1px solid ${t.mark}` : 'none',
        boxShadow: live ? `0 0 0 3px color-mix(in oklab, ${t.mark} 20%, transparent)` : 'none'
      }
    }), showLabels ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: `var(--fw-medium) ${compact ? 'var(--fs-10)' : 'var(--fs-11)'}/1 var(--font-mono)`,
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: t.fg,
        whiteSpace: 'nowrap'
      }
    }, link) : null), i < LINKS.length - 1 ? /*#__PURE__*/React.createElement("span", {
      style: {
        width: compact ? 10 : 18,
        height: 1,
        flex: compact ? '0 0 auto' : '1 1 auto',
        minWidth: 8,
        background: 'var(--border-subtle)'
      }
    }) : null);
  }), detail ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)',
      marginLeft: 6,
      whiteSpace: 'nowrap'
    }
  }, detail) : null);
}
Object.assign(__ds_scope, { CausalChain });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/pipeline/CausalChain.jsx", error: String((e && e.message) || e) }); }

// components/status/ReliabilityMeter.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function ReliabilityMeter({
  label,
  value,
  target,
  unit = '%',
  bars = 24,
  tone = 'allowed',
  style,
  ...rest
}) {
  const pct = Math.max(0, Math.min(100, value));
  const filled = Math.round(pct / 100 * bars);
  const color = tone === 'blocked' ? 'var(--status-blocked-dot)' : tone === 'escalated' ? 'var(--status-escalated-dot)' : 'var(--status-allowed-dot)';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      minWidth: 0,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)'
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--fw-medium) var(--fs-13)/1 var(--font-mono)',
      fontVariantNumeric: 'tabular-nums'
    }
  }, value, unit)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 2,
      alignItems: 'flex-end',
      height: 12
    }
  }, Array.from({
    length: bars
  }).map((_, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      flex: 1,
      height: i < filled ? 12 : 6,
      background: i < filled ? color : 'var(--ink-150)',
      borderRadius: 1
    }
  }))), target ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-caption)',
      color: 'var(--text-tertiary)'
    }
  }, target) : null);
}
Object.assign(__ds_scope, { ReliabilityMeter });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/ReliabilityMeter.jsx", error: String((e && e.message) || e) }); }

// components/status/SeverityDot.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const DOT = {
  allowed: 'var(--status-allowed-dot)',
  blocked: 'var(--status-blocked-dot)',
  escalated: 'var(--status-escalated-dot)',
  failed: 'var(--status-failed-dot)',
  conflict: 'var(--status-conflict-dot)',
  pending: 'var(--status-pending-dot)'
};
function SeverityDot({
  status = 'pending',
  label,
  pulse = false,
  size = 7,
  style,
  ...rest
}) {
  const color = DOT[status] || DOT.pending;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      width: size,
      height: size,
      borderRadius: 'var(--radius-pill)',
      background: color,
      flex: '0 0 auto',
      boxShadow: pulse ? `0 0 0 3px color-mix(in oklab, ${color} 22%, transparent)` : 'none'
    }
  }), label ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--text-secondary)'
    }
  }, label) : null);
}
Object.assign(__ds_scope, { SeverityDot });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/SeverityDot.jsx", error: String((e && e.message) || e) }); }

// components/status/StatusBadge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const MAP = {
  allowed: {
    label: 'Allowed',
    icon: 'check',
    fg: 'var(--status-allowed-fg)',
    bg: 'var(--status-allowed-bg)'
  },
  blocked: {
    label: 'Blocked',
    icon: 'shield-x',
    fg: 'var(--status-blocked-fg)',
    bg: 'var(--status-blocked-bg)'
  },
  escalated: {
    label: 'Escalated',
    icon: 'arrow-up-right',
    fg: 'var(--status-escalated-fg)',
    bg: 'var(--status-escalated-bg)'
  },
  failed: {
    label: 'Failed',
    icon: 'triangle-alert',
    fg: 'var(--status-failed-fg)',
    bg: 'var(--status-failed-bg)'
  },
  conflict: {
    label: 'Conflict',
    icon: 'git-compare',
    fg: 'var(--status-conflict-fg)',
    bg: 'var(--status-conflict-bg)'
  },
  pending: {
    label: 'Pending',
    icon: 'clock',
    fg: 'var(--status-pending-fg)',
    bg: 'var(--status-pending-bg)'
  },
  review: {
    label: 'In review',
    icon: 'message-square',
    fg: 'var(--blue-700)',
    bg: 'var(--blue-50)'
  }
};
function StatusBadge({
  status = 'pending',
  children,
  showIcon = true,
  size = 'md',
  style,
  ...rest
}) {
  const s = MAP[status] || MAP.pending;
  const lg = size === 'lg';
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      height: lg ? 24 : 20,
      padding: lg ? '0 9px' : '0 7px',
      borderRadius: 'var(--radius-3)',
      background: s.bg,
      color: s.fg,
      font: `var(--fw-medium) ${lg ? 'var(--fs-12)' : 'var(--fs-11)'}/1 var(--font-sans)`,
      letterSpacing: 'var(--ls-caps)',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      ...style
    }
  }, rest), showIcon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: s.icon,
    size: lg ? 13 : 12
  }) : null, children || s.label);
}
Object.assign(__ds_scope, { StatusBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/StatusBadge.jsx", error: String((e && e.message) || e) }); }

// components/governance/CaseRow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function CaseRow({
  id,
  title,
  status,
  agentConflict = false,
  surface,
  amount,
  time,
  selected = false,
  onClick,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", _extends({
    role: "row",
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: 'grid',
      gridTemplateColumns: '104px minmax(0,1fr) auto 96px 108px 68px',
      alignItems: 'center',
      gap: 12,
      height: 'var(--row-height)',
      padding: '0 14px',
      borderBottom: '1px solid var(--border-hairline)',
      cursor: 'pointer',
      background: selected ? 'var(--bg-selected)' : hover ? 'var(--bg-hover)' : 'transparent',
      boxShadow: selected ? 'inset 2px 0 0 var(--accent)' : 'none',
      transition: 'var(--transition-control)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-secondary)'
    }
  }, id), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 7,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: `${selected ? 'var(--fw-medium)' : 'var(--fw-regular)'} var(--fs-13)/1.3 var(--font-sans)`,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, title), agentConflict ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "git-compare",
    size: 13,
    style: {
      color: 'var(--status-conflict-dot)'
    },
    title: "Agent disagreement"
  }) : null), /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: status
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--text-secondary)',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, surface), /*#__PURE__*/React.createElement("span", {
    "data-numeric": true,
    style: {
      font: 'var(--type-mono)',
      fontSize: 'var(--fs-13)',
      textAlign: 'right'
    }
  }, amount), /*#__PURE__*/React.createElement("span", {
    "data-numeric": true,
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)',
      textAlign: 'right'
    }
  }, time));
}
Object.assign(__ds_scope, { CaseRow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/governance/CaseRow.jsx", error: String((e && e.message) || e) }); }

// components/governance/DecisionSummary.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function DecisionSummary({
  outcome = 'blocked',
  headline,
  policy,
  reasons = [],
  decidedAt,
  decidedBy = 'GOVERN',
  style,
  ...rest
}) {
  const accent = {
    allowed: 'var(--status-allowed-dot)',
    blocked: 'var(--status-blocked-dot)',
    escalated: 'var(--status-escalated-dot)',
    failed: 'var(--status-failed-dot)'
  }[outcome] || 'var(--ink-300)';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      padding: '14px 16px',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-subtle)',
      borderTop: `2px solid ${accent}`,
      borderRadius: 'var(--radius-4)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: outcome,
    size: "lg"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-heading)',
      letterSpacing: 'var(--ls-heading)',
      textWrap: 'pretty'
    }
  }, headline)), reasons.length ? /*#__PURE__*/React.createElement("ul", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 7,
      margin: 0,
      padding: 0,
      listStyle: 'none'
    }
  }, reasons.map((r, i) => /*#__PURE__*/React.createElement("li", {
    key: i,
    style: {
      display: 'grid',
      gridTemplateColumns: '78px minmax(0,1fr)',
      gap: 12,
      font: 'var(--type-body-sm)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)',
      paddingTop: 3
    }
  }, r.label), /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-primary)',
      textWrap: 'pretty'
    }
  }, r.value)))) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 14,
      paddingTop: 2,
      borderTop: '1px solid var(--border-hairline)',
      paddingTop: 10,
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)',
      flexWrap: 'wrap'
    }
  }, policy ? /*#__PURE__*/React.createElement("span", null, "policy ", policy) : null, /*#__PURE__*/React.createElement("span", null, "decided by ", decidedBy), decidedAt ? /*#__PURE__*/React.createElement("span", {
    "data-numeric": true
  }, decidedAt) : null));
}
Object.assign(__ds_scope, { DecisionSummary });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/governance/DecisionSummary.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/KeyValue.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function KeyValue({
  items = [],
  columns = 1,
  dense = false,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("dl", _extends({
    style: {
      display: 'grid',
      gridTemplateColumns: `repeat(${columns}, minmax(0,1fr))`,
      gap: dense ? '6px 24px' : '10px 24px',
      margin: 0,
      ...style
    }
  }, rest), items.map((it, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("dt", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: 'var(--text-tertiary)'
    }
  }, it.label), /*#__PURE__*/React.createElement("dd", {
    style: {
      margin: 0,
      minWidth: 0,
      font: it.mono ? 'var(--type-mono)' : 'var(--type-body-sm)',
      fontSize: it.mono ? 'var(--fs-13)' : undefined,
      color: 'var(--text-primary)',
      fontVariantNumeric: 'tabular-nums',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, it.value))));
}
Object.assign(__ds_scope, { KeyValue });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/KeyValue.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Panel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Panel({
  title,
  label,
  actions,
  footer,
  padded = true,
  tone = 'surface',
  children,
  style,
  bodyStyle,
  ...rest
}) {
  const dark = tone === 'console';
  return /*#__PURE__*/React.createElement("section", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      minWidth: 0,
      background: dark ? 'var(--bg-console)' : tone === 'inset' ? 'var(--bg-inset)' : 'var(--bg-surface)',
      border: `1px solid ${dark ? 'var(--border-console)' : 'var(--border-subtle)'}`,
      borderRadius: 'var(--radius-6)',
      color: dark ? 'var(--text-inverse)' : 'inherit',
      ...style
    }
  }, rest), title || label || actions ? /*#__PURE__*/React.createElement("header", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      minHeight: 40,
      padding: '0 12px 0 14px',
      borderBottom: `1px solid ${dark ? 'var(--border-console)' : 'var(--border-hairline)'}`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      gap: 8,
      minWidth: 0
    }
  }, label ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-label)',
      letterSpacing: 'var(--ls-label)',
      textTransform: 'uppercase',
      color: dark ? 'var(--text-inverse-secondary)' : 'var(--text-tertiary)'
    }
  }, label) : null, title ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-subheading)',
      letterSpacing: 'var(--ls-heading)',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, title) : null), actions ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6
    }
  }, actions) : null) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0,
      padding: padded ? 'var(--space-14, 14px)' : 0,
      ...bodyStyle
    }
  }, children), footer ? /*#__PURE__*/React.createElement("footer", {
    style: {
      padding: '10px 14px',
      borderTop: `1px solid ${dark ? 'var(--border-console)' : 'var(--border-hairline)'}`,
      font: 'var(--type-caption)',
      color: dark ? 'var(--text-inverse-secondary)' : 'var(--text-secondary)'
    }
  }, footer) : null);
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Panel.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/SectionHeader.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function SectionHeader({
  title,
  meta,
  description,
  actions,
  size = 'md',
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      justifyContent: 'space-between',
      gap: 16,
      paddingBottom: 10,
      borderBottom: '1px solid var(--border-hairline)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 3,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      font: size === 'lg' ? 'var(--type-title)' : 'var(--type-heading)',
      letterSpacing: 'var(--ls-heading)'
    }
  }, title), meta ? /*#__PURE__*/React.createElement("span", {
    style: {
      font: 'var(--type-mono)',
      color: 'var(--text-tertiary)'
    }
  }, meta) : null), description ? /*#__PURE__*/React.createElement("p", {
    style: {
      font: 'var(--type-body-sm)',
      color: 'var(--text-secondary)',
      maxWidth: '68ch',
      textWrap: 'pretty'
    }
  }, description) : null), actions ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      flex: '0 0 auto'
    }
  }, actions) : null);
}
Object.assign(__ds_scope, { SectionHeader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/SectionHeader.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Audit.jsx
try { (() => {
(() => {
  const {
    Input,
    Button
  } = window.SentinelDesignSystem_8a81b0;
  const STAGES = ['all', 'intake', 'agents', 'conflict', 'govern', 'executor', 'reviewer', 'system'];
  const STAGE_COLOR = {
    govern: 'var(--text-primary)',
    conflict: 'var(--status-conflict-fg)',
    executor: 'var(--teal)',
    reviewer: 'var(--status-escalated-fg)'
  };
  function Audit({
    audit
  }) {
    const [stage, setStage] = React.useState('all');
    const entries = stage === 'all' ? audit : audit.filter(e => String(e.actor) === stage);
    return /*#__PURE__*/React.createElement("div", {
      style: {
        overflow: 'auto',
        height: '100%'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1120,
        margin: '0 auto',
        padding: '44px 28px 80px',
        display: 'flex',
        flexDirection: 'column',
        gap: 24
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'flex-end',
        gap: 24,
        flexWrap: 'wrap'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)',
        letterSpacing: '-0.022em'
      }
    }, "Audit"), /*#__PURE__*/React.createElement("p", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, "Append-only. 18,402 entries over 30 days \xB7 retention 7 years.")), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Input, {
      icon: "search",
      mono: true,
      placeholder: "case, policy or reference",
      wrapperStyle: {
        width: 230
      }
    }), /*#__PURE__*/React.createElement(Button, {
      size: "md",
      variant: "ghost",
      icon: "download"
    }, "Export")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        borderBottom: '1px solid var(--border-hairline)',
        flexWrap: 'wrap'
      }
    }, STAGES.map(s => {
      const active = stage === s;
      return /*#__PURE__*/React.createElement("button", {
        key: s,
        type: "button",
        onClick: () => setStage(s),
        style: {
          position: 'relative',
          height: 30,
          border: 0,
          background: 'none',
          padding: 0,
          cursor: 'pointer',
          color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
          font: 'var(--type-mono)',
          transition: 'var(--transition-control)'
        }
      }, s, /*#__PURE__*/React.createElement("span", {
        style: {
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: -1,
          height: 1,
          background: active ? 'var(--text-primary)' : 'transparent'
        }
      }));
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column'
      }
    }, entries.map((e, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: 'grid',
        gridTemplateColumns: '132px 96px minmax(0,1fr) 220px',
        gap: 20,
        alignItems: 'baseline',
        padding: '9px 0',
        borderBottom: i === entries.length - 1 ? 0 : '1px solid var(--border-hairline)',
        minWidth: 700
      }
    }, /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, e.time), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: STAGE_COLOR[e.actor] || 'var(--text-secondary)'
      }
    }, e.actor), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        textWrap: 'pretty'
      }
    }, e.message), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, e.detail || '—')))), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-caption)',
        color: 'var(--text-tertiary)'
      }
    }, "Showing ", entries.length, " of 18,402 entries. Entries cannot be edited or removed, including reviewer annotations.")));
  }
  Object.assign(window, {
    Audit
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Audit.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Cases.jsx
try { (() => {
(() => {
  const {
    Input
  } = window.SentinelDesignSystem_8a81b0;
  const {
    Outcome
  } = window;
  const QUEUES = [{
    value: 'attention',
    label: 'Needs attention'
  }, {
    value: 'all',
    label: 'All'
  }, {
    value: 'allowed',
    label: 'Executed'
  }];
  function Row({
    c,
    onOpen,
    last
  }) {
    const [hover, setHover] = React.useState(false);
    return /*#__PURE__*/React.createElement("div", {
      onClick: () => onOpen(c.id),
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
      style: {
        display: 'grid',
        gridTemplateColumns: '108px minmax(0,1.6fr) 180px minmax(0,1fr) 92px',
        gap: 20,
        alignItems: 'baseline',
        padding: '15px 8px 15px 0',
        minWidth: 720,
        cursor: 'pointer',
        borderBottom: last ? 0 : '1px solid var(--border-hairline)',
        background: hover ? 'var(--bg-hover)' : 'transparent',
        transition: 'var(--transition-control)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, c.id), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-medium) var(--fs-14)/1.3 var(--font-sans)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, c.title), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-tertiary)'
      }
    }, c.domain, " \xB7 ", c.value), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, c.shortReason), /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        justifyContent: 'flex-end'
      }
    }, /*#__PURE__*/React.createElement(Outcome, {
      status: c.status
    })));
  }
  function Cases({
    cases,
    onOpen
  }) {
    const [queue, setQueue] = React.useState('attention');
    const list = cases.filter(c => queue === 'all' ? true : queue === 'attention' ? ['blocked', 'escalated', 'failed'].includes(c.status) : c.status === 'allowed');
    const n = v => v === 'all' ? cases.length : v === 'attention' ? cases.filter(c => ['blocked', 'escalated', 'failed'].includes(c.status)).length : cases.filter(c => c.status === 'allowed').length;
    return /*#__PURE__*/React.createElement("div", {
      style: {
        overflow: 'auto',
        height: '100%'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1080,
        margin: '0 auto',
        padding: '44px 28px 72px',
        display: 'flex',
        flexDirection: 'column',
        gap: 26
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'flex-end',
        gap: 24,
        flexWrap: 'wrap'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)',
        letterSpacing: '-0.022em'
      }
    }, "Cases"), /*#__PURE__*/React.createElement("p", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, "Automated actions Sentinel decided on. Open one to see why.")), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Input, {
      icon: "search",
      placeholder: "Case, surface or policy",
      mono: true,
      wrapperStyle: {
        width: 220
      }
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 22,
        borderBottom: '1px solid var(--border-hairline)'
      }
    }, QUEUES.map(q => {
      const active = queue === q.value;
      return /*#__PURE__*/React.createElement("button", {
        key: q.value,
        type: "button",
        onClick: () => setQueue(q.value),
        style: {
          position: 'relative',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          height: 32,
          padding: 0,
          border: 0,
          background: 'none',
          cursor: 'pointer',
          color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
          font: 'var(--fw-medium) var(--fs-13)/1 var(--font-sans)',
          transition: 'var(--transition-control)'
        }
      }, q.label, /*#__PURE__*/React.createElement("span", {
        "data-numeric": true,
        style: {
          font: 'var(--type-mono)',
          color: 'var(--text-tertiary)'
        }
      }, n(q.value)), /*#__PURE__*/React.createElement("span", {
        style: {
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: -1,
          height: 1,
          background: active ? 'var(--text-primary)' : 'transparent'
        }
      }));
    })), /*#__PURE__*/React.createElement("div", null, list.map((c, i) => /*#__PURE__*/React.createElement(Row, {
      key: c.id,
      c: c,
      onOpen: onOpen,
      last: i === list.length - 1
    }))), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-caption)',
        color: 'var(--text-tertiary)'
      }
    }, "Reasoning, candidates, execution and audit detail live inside each case.")));
  }
  Object.assign(window, {
    Cases
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Cases.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Data.jsx
try { (() => {
(() => {
  const CASES = [{
    id: 'CASE-2041',
    title: 'Vendor payout above ceiling',
    status: 'blocked',
    conflict: true,
    surface: 'payouts.settle',
    amount: '₹18,40,000',
    time: '14:02',
    opened: '14:02:11.402 IST',
    policy: 'payout-v4',
    latency: '3.2s',
    agents: 2,
    chain: {
      agents: 'passed',
      conflict: 'conflict',
      resolve: 'passed',
      weigh: 'passed',
      govern: 'blocked',
      executor: 'halted'
    },
    chainDetail: 'halted at GOVERN · policy payout-v4',
    headline: 'Execution blocked before any external call.',
    reasons: [{
      label: 'Trigger',
      value: 'Requested amount exceeds the vendor ceiling by 41%.'
    }, {
      label: 'Conflict',
      value: 'risk-agent and settlement-agent disagreed on reversibility within SLA.'
    }, {
      label: 'Effect',
      value: 'No payout request was issued. Funds remain held.'
    }],
    stages: [{
      label: 'Intake',
      state: 'done',
      detail: '14:02:11'
    }, {
      label: 'Weigh',
      state: 'done',
      detail: '3 candidates'
    }, {
      label: 'Govern',
      state: 'blocked',
      detail: 'policy payout-v4'
    }, {
      label: 'Execution',
      state: 'skipped',
      detail: 'not reached'
    }, {
      label: 'Review',
      state: 'active',
      detail: 'annotation open'
    }],
    candidates: [{
      rank: '01',
      name: 'Hold payout for manual settlement',
      proposedBy: 'risk-agent v7',
      score: '0.82',
      verdict: 'chosen',
      rationale: 'Lowest exposure; reversible within SLA.'
    }, {
      rank: '02',
      name: 'Release with partial amount',
      proposedBy: 'settlement-agent v3',
      score: '0.61',
      verdict: 'rejected',
      rationale: 'Still breaches the vendor ceiling policy.'
    }, {
      rank: '03',
      name: 'Defer 6h and re-evaluate',
      proposedBy: 'risk-agent v7',
      score: '0.44',
      verdict: 'considered',
      rationale: 'Reversal window closes before the next evaluation.'
    }],
    conflictSubject: 'Reversibility of the payout within SLA',
    positions: [{
      agent: 'risk-agent v7',
      position: 'Hold',
      basis: 'Vendor ceiling breached; counterparty unseen for 90 days.',
      confidence: '0.82'
    }, {
      agent: 'settlement-agent v3',
      position: 'Release',
      basis: 'Reversal window open for a further 6 hours.',
      confidence: '0.61'
    }],
    audit: [{
      time: '14:02:11.402',
      actor: 'intake',
      actorKind: 'system',
      message: 'Case opened from payout webhook',
      detail: 'src payouts.settle'
    }, {
      time: '14:02:12.118',
      actor: 'agents',
      actorKind: 'agent',
      message: 'risk-agent v7 proposed 2 options'
    }, {
      time: '14:02:13.907',
      actor: 'conflict',
      actorKind: 'agent',
      message: 'Conflict detected between 2 agents',
      detail: 'subject reversibility'
    }, {
      time: '14:02:13.988',
      actor: 'resolve',
      actorKind: 'agent',
      message: 'Positions reconciled into 3 candidates'
    }, {
      time: '14:02:14.061',
      actor: 'weigh',
      actorKind: 'agent',
      message: 'Scored 3 candidates',
      detail: 'top 0.82'
    }, {
      time: '14:02:14.118',
      actor: 'govern',
      actorKind: 'govern',
      message: 'Blocked',
      detail: 'policy payout-v4 · rule ceiling.vendor'
    }, {
      time: '14:02:14.121',
      actor: 'executor',
      actorKind: 'execution',
      message: 'No call issued',
      detail: 'stage halted'
    }, {
      time: '14:04:02.220',
      actor: 'reviewer',
      actorKind: 'reviewer',
      message: 'Annotation recorded',
      detail: 'no authority change'
    }],
    notes: [{
      who: 'p.rao',
      when: '14:04',
      text: 'Vendor ceiling is stale — finance raised it last quarter. Flagged to the policy owner.'
    }],
    exec: null
  }, {
    id: 'CASE-2043',
    title: 'Vendor onboarding KYC mismatch',
    status: 'escalated',
    conflict: true,
    surface: 'onboarding.activate',
    amount: '—',
    time: '13:41',
    opened: '13:41:19.220 IST',
    policy: 'kyc-v9',
    latency: '2.8s',
    agents: 2,
    chain: {
      agents: 'passed',
      conflict: 'conflict',
      resolve: 'passed',
      weigh: 'passed',
      govern: 'escalated',
      executor: 'halted'
    },
    chainDetail: 'escalated at GOVERN · awaiting review',
    headline: 'Escalated for human review before any activation.',
    reasons: [{
      label: 'Trigger',
      value: 'Registered name differs from the bank beneficiary name.'
    }, {
      label: 'Conflict',
      value: 'kyc-agent and docs-agent disagreed on match confidence.'
    }, {
      label: 'Effect',
      value: 'Activation held. No payout capability granted.'
    }],
    stages: [{
      label: 'Intake',
      state: 'done',
      detail: '13:41:19'
    }, {
      label: 'Weigh',
      state: 'done',
      detail: '2 candidates'
    }, {
      label: 'Govern',
      state: 'halted',
      detail: 'escalated'
    }, {
      label: 'Execution',
      state: 'pending',
      detail: 'held'
    }, {
      label: 'Review',
      state: 'active',
      detail: '2 notes'
    }],
    candidates: [{
      rank: '01',
      name: 'Hold activation pending document review',
      proposedBy: 'kyc-agent v4',
      score: '0.74',
      verdict: 'chosen',
      rationale: 'Name mismatch outside tolerance.'
    }, {
      rank: '02',
      name: 'Activate with limited payout cap',
      proposedBy: 'docs-agent v2',
      score: '0.58',
      verdict: 'rejected',
      rationale: 'Not permitted for unverified beneficiaries.'
    }],
    conflictSubject: 'Confidence of the beneficiary name match',
    positions: [{
      agent: 'kyc-agent v4',
      position: 'Hold',
      basis: 'Fuzzy name match 0.71 — below the 0.85 threshold.',
      confidence: '0.74'
    }, {
      agent: 'docs-agent v2',
      position: 'Activate capped',
      basis: 'Registration certificate and PAN agree.',
      confidence: '0.58'
    }],
    audit: [{
      time: '13:41:19.220',
      actor: 'intake',
      actorKind: 'system',
      message: 'Case opened from onboarding submission'
    }, {
      time: '13:41:21.884',
      actor: 'conflict',
      actorKind: 'agent',
      message: 'Conflict detected between 2 agents'
    }, {
      time: '13:41:22.017',
      actor: 'govern',
      actorKind: 'govern',
      message: 'Escalated',
      detail: 'policy kyc-v9 · rule name.match'
    }],
    notes: [{
      who: 'a.mehta',
      when: '13:52',
      text: 'Beneficiary name matches the parent entity, not the registered vendor. Documents requested.'
    }, {
      who: 'p.rao',
      when: '14:01',
      text: 'Second document received; still awaiting bank confirmation.'
    }],
    exec: null
  }, {
    id: 'CASE-2044',
    title: 'Settlement webhook replay',
    status: 'failed',
    surface: 'settlements.replay',
    amount: '₹6,12,400',
    time: '12:20',
    opened: '12:20:44.010 IST',
    policy: 'settle-v1',
    latency: '1.9s',
    agents: 1,
    chain: {
      agents: 'passed',
      conflict: 'clear',
      resolve: 'passed',
      weigh: 'passed',
      govern: 'passed',
      executor: 'blocked'
    },
    chainDetail: 'execution failed · HTTP 503 upstream',
    headline: 'Allowed by GOVERN; execution failed at the downstream API.',
    reasons: [{
      label: 'Trigger',
      value: 'Replay of 3 settlement webhooks after a partner outage.'
    }, {
      label: 'Failure',
      value: 'Partner returned 503 on attempt 2 of 3; no partial state written.'
    }, {
      label: 'Effect',
      value: 'Case held for re-evaluation. No automatic retry.'
    }],
    stages: [{
      label: 'Intake',
      state: 'done',
      detail: '12:20:44'
    }, {
      label: 'Weigh',
      state: 'done',
      detail: '1 candidate'
    }, {
      label: 'Govern',
      state: 'done',
      detail: 'allowed'
    }, {
      label: 'Execution',
      state: 'blocked',
      detail: '503 upstream'
    }, {
      label: 'Review',
      state: 'active',
      detail: 'annotation open'
    }],
    candidates: [{
      rank: '01',
      name: 'Replay all 3 webhooks',
      proposedBy: 'settlement-agent v3',
      score: '0.88',
      verdict: 'chosen',
      rationale: 'Idempotent; partner reported recovery.'
    }],
    conflictSubject: null,
    positions: [],
    audit: [{
      time: '12:20:44.010',
      actor: 'intake',
      actorKind: 'system',
      message: 'Case opened from partner recovery signal'
    }, {
      time: '12:20:45.332',
      actor: 'govern',
      actorKind: 'govern',
      message: 'Allowed',
      detail: 'policy settle-v1'
    }, {
      time: '12:20:46.901',
      actor: 'executor',
      actorKind: 'execution',
      message: 'Failed on attempt 2/3',
      detail: 'HTTP 503 · no partial write'
    }],
    notes: [],
    exec: {
      id: 'EXEC-8830',
      target: 'settlements.replay',
      duration: '1.9s',
      result: 'Failed · HTTP 503',
      at: '12:20:46 IST'
    }
  }, {
    id: 'CASE-2042',
    title: 'Refund batch retry',
    status: 'allowed',
    surface: 'refunds.batch.retry',
    amount: '₹42,900',
    time: '13:58',
    opened: '13:58:02.004 IST',
    policy: 'refund-v2',
    latency: '1.4s',
    agents: 1,
    chain: {
      agents: 'passed',
      conflict: 'clear',
      resolve: 'passed',
      weigh: 'passed',
      govern: 'passed',
      executor: 'passed'
    },
    chainDetail: 'executed · 412ms · 14/14',
    headline: 'Execution allowed and completed on the first attempt.',
    reasons: [{
      label: 'Trigger',
      value: 'Retry of 14 refunds failed by an upstream timeout.'
    }, {
      label: 'Basis',
      value: 'All amounts inside per-item and batch ceilings.'
    }],
    stages: [{
      label: 'Intake',
      state: 'done',
      detail: '13:58:02'
    }, {
      label: 'Weigh',
      state: 'done',
      detail: '2 candidates'
    }, {
      label: 'Govern',
      state: 'done',
      detail: 'allowed'
    }, {
      label: 'Execution',
      state: 'done',
      detail: '412ms · 14/14'
    }, {
      label: 'Review',
      state: 'skipped',
      detail: 'not required'
    }],
    candidates: [{
      rank: '01',
      name: 'Retry all 14 refunds now',
      proposedBy: 'settlement-agent v3',
      score: '0.91',
      verdict: 'chosen',
      rationale: 'Upstream healthy for 6 minutes.'
    }, {
      rank: '02',
      name: 'Stagger retries over 10 minutes',
      proposedBy: 'settlement-agent v3',
      score: '0.55',
      verdict: 'rejected',
      rationale: 'Breaches the customer refund SLA.'
    }],
    conflictSubject: null,
    positions: [],
    audit: [{
      time: '13:58:02.004',
      actor: 'intake',
      actorKind: 'system',
      message: 'Case opened from retry scheduler'
    }, {
      time: '13:58:03.551',
      actor: 'govern',
      actorKind: 'govern',
      message: 'Allowed',
      detail: 'policy refund-v2'
    }, {
      time: '13:58:03.963',
      actor: 'executor',
      actorKind: 'execution',
      message: 'Completed 14/14',
      detail: 'EXEC-8841 · 412ms'
    }],
    notes: [],
    exec: {
      id: 'EXEC-8841',
      target: 'refunds.batch.retry',
      duration: '412ms',
      result: '14 of 14 succeeded',
      at: '13:58:03 IST'
    }
  }];
  const CHAIN_THROUGHPUT = [{
    link: 'Agents',
    value: 412,
    note: 'proposals · 24h'
  }, {
    link: 'Conflict',
    value: 38,
    note: 'disagreements'
  }, {
    link: 'Resolve',
    value: 38,
    note: 'reconciled'
  }, {
    link: 'Weigh',
    value: 412,
    note: 'candidate sets scored'
  }, {
    link: 'Govern',
    value: 412,
    note: '396 allowed · 12 blocked · 4 escalated'
  }, {
    link: 'Executor',
    value: 396,
    note: '394 succeeded · 2 failed'
  }];
  const RELIABILITY = [{
    label: 'Execution success',
    value: 99.4,
    target: 'target 99.5% · trailing 30d',
    tone: 'allowed'
  }, {
    label: 'Govern latency budget',
    value: 82,
    target: 'p99 118ms of 150ms',
    tone: 'escalated'
  }, {
    label: 'Agent agreement',
    value: 64,
    target: '12 conflicts today',
    tone: 'blocked'
  }, {
    label: 'Audit completeness',
    value: 100,
    target: 'no gaps in 30d',
    tone: 'allowed'
  }];
  const EXECUTORS = [{
    region: 'ap-south-1',
    state: 'allowed',
    depth: '0',
    last: '412ms',
    note: 'Healthy'
  }, {
    region: 'eu-west-1',
    state: 'allowed',
    depth: '2',
    last: '388ms',
    note: 'Healthy'
  }, {
    region: 'us-east-1',
    state: 'escalated',
    depth: '9',
    last: '1.9s',
    note: 'Partner 503s'
  }];
  const GLOBAL_AUDIT = [{
    time: '14:04:02.220',
    actor: 'reviewer',
    actorKind: 'reviewer',
    message: 'Annotation recorded on CASE-2041',
    detail: 'p.rao · no authority change'
  }, {
    time: '14:02:14.118',
    actor: 'govern',
    actorKind: 'govern',
    message: 'Blocked CASE-2041',
    detail: 'policy payout-v4 · rule ceiling.vendor'
  }, {
    time: '14:02:13.907',
    actor: 'conflict',
    actorKind: 'agent',
    message: 'Conflict detected · CASE-2041',
    detail: '2 agents · reversibility'
  }, {
    time: '13:58:03.963',
    actor: 'executor',
    actorKind: 'execution',
    message: 'Completed EXEC-8841',
    detail: '412ms · ap-south-1'
  }, {
    time: '13:58:03.551',
    actor: 'govern',
    actorKind: 'govern',
    message: 'Allowed CASE-2042',
    detail: 'policy refund-v2'
  }, {
    time: '13:41:22.017',
    actor: 'govern',
    actorKind: 'govern',
    message: 'Escalated CASE-2043',
    detail: 'policy kyc-v9 · rule name.match'
  }, {
    time: '12:20:46.901',
    actor: 'executor',
    actorKind: 'execution',
    message: 'Failed EXEC-8830',
    detail: 'HTTP 503 · us-east-1'
  }, {
    time: '12:20:45.332',
    actor: 'govern',
    actorKind: 'govern',
    message: 'Allowed CASE-2044',
    detail: 'policy settle-v1'
  }, {
    time: '11:04:00.000',
    actor: 'system',
    actorKind: 'system',
    message: 'Policy bundle deployed',
    detail: '18 policies · rev 214'
  }];
  const SCENARIO = [{
    t: '00.0s',
    link: 'Agents',
    title: 'Three agents propose',
    body: 'risk-agent, settlement-agent and ledger-agent each return a position on a ₹18.4L vendor payout.',
    chain: {
      agents: 'active'
    }
  }, {
    t: '01.7s',
    link: 'Conflict',
    title: 'Positions disagree',
    body: 'risk-agent says hold; settlement-agent says release. The disagreement is on reversibility, not on the amount.',
    chain: {
      agents: 'passed',
      conflict: 'active'
    }
  }, {
    t: '01.8s',
    link: 'Resolve',
    title: 'Disagreement reconciled',
    body: 'Positions collapse into three mutually exclusive candidate options — no agent wins by rank.',
    chain: {
      agents: 'passed',
      conflict: 'conflict',
      resolve: 'active'
    }
  }, {
    t: '02.4s',
    link: 'Weigh',
    title: 'Candidates scored',
    body: 'Each option is scored on exposure, reversibility and SLA. Highest score: hold for manual settlement at 0.82.',
    chain: {
      agents: 'passed',
      conflict: 'conflict',
      resolve: 'passed',
      weigh: 'active'
    }
  }, {
    t: '03.2s',
    link: 'Govern',
    title: 'GOVERN blocks',
    body: 'Policy payout-v4 rule ceiling.vendor is breached by 41%. The decision is blocked, with reasons recorded.',
    chain: {
      agents: 'passed',
      conflict: 'conflict',
      resolve: 'passed',
      weigh: 'passed',
      govern: 'active'
    }
  }, {
    t: '03.2s',
    link: 'Executor',
    title: 'Nothing executes',
    body: 'The executor is never called. No payout request leaves the control plane; the case routes to human review for annotation.',
    chain: {
      agents: 'passed',
      conflict: 'conflict',
      resolve: 'passed',
      weigh: 'passed',
      govern: 'blocked',
      executor: 'halted'
    }
  }];

  /* Level-1 summary fields: what an operator needs before opening the case. */
  const SUMMARY = {
    'CASE-2041': {
      domain: 'Payouts',
      value: '₹18.4L',
      shortReason: 'Vendor ceiling exceeded by 41%'
    },
    'CASE-2043': {
      domain: 'Onboarding',
      value: 'KYC',
      shortReason: 'Beneficiary name outside match tolerance'
    },
    'CASE-2044': {
      domain: 'Settlements',
      value: '₹6.1L',
      shortReason: 'Partner returned 503 mid-replay'
    },
    'CASE-2042': {
      domain: 'Refunds',
      value: '₹42.9K',
      shortReason: 'Inside all ceilings'
    }
  };
  CASES.forEach(c => Object.assign(c, SUMMARY[c.id]));
  Object.assign(window, {
    CASES,
    CHAIN_THROUGHPUT,
    RELIABILITY,
    EXECUTORS,
    GLOBAL_AUDIT,
    SCENARIO
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Data.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/DecisionRecord.jsx
try { (() => {
(() => {
  const {
    Button,
    Textarea,
    Dialog,
    AuditTrail,
    Icon
  } = window.SentinelDesignSystem_8a81b0;
  const {
    Disclosure
  } = window;

  /* One state table drives the whole record, so all four outcomes stay honest and consistent. */
  const STATE = {
    blocked: {
      verdict: 'Blocked',
      tone: 'var(--status-blocked-fg)',
      authority: 'Denied',
      govern: 'GOVERN denied execution.',
      execLead: 'Not reached',
      execTone: '#D2664E'
    },
    escalated: {
      verdict: 'Escalated',
      tone: 'var(--status-escalated-fg)',
      authority: 'Withheld',
      govern: 'GOVERN did not authorise autonomous execution and routed the case for human review.',
      execLead: 'Not executed',
      execTone: 'var(--status-escalated-fg)'
    },
    failed: {
      verdict: 'Failed',
      tone: '#D96B6B',
      authority: 'Granted',
      decision: 'Allowed',
      govern: 'GOVERN allowed the action; the failure happened downstream.',
      execLead: 'Execution failed',
      execTone: '#D96B6B'
    },
    allowed: {
      verdict: 'Executed',
      tone: 'var(--status-allowed-fg)',
      authority: 'Granted',
      decision: 'Allowed',
      govern: 'GOVERN authorised the action.',
      execLead: 'Executed successfully',
      execTone: 'var(--status-allowed-fg)'
    }
  };
  const MARK = {
    stop: 'var(--status-blocked-fg)',
    hold: 'var(--status-escalated-fg)',
    split: 'var(--status-conflict-fg)',
    none: 'var(--border-emphasis)'
  };

  /* Compact supporting stage: label, one line, optional evidence. Never competes with the verdict. */
  function Stage({
    label,
    mark = 'none',
    summary,
    children,
    last = false
  }) {
    const filled = mark !== 'none';
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'grid',
        gridTemplateColumns: '92px 11px minmax(0,1fr)',
        columnGap: 20,
        alignItems: 'stretch'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        paddingTop: 2,
        textAlign: 'right'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        fontSize: filled ? 'var(--fs-16)' : 'var(--fs-15)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: filled ? MARK[mark] : 'var(--text-secondary)'
      }
    }, label)), /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'relative',
        display: 'flex',
        justifyContent: 'center'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 1,
        background: last ? 'transparent' : 'var(--border-subtle)'
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        top: 5,
        width: 5,
        height: 5,
        borderRadius: 99,
        background: filled ? MARK[mark] : 'var(--border-emphasis)',
        boxShadow: '0 0 0 4px var(--bg-app)'
      }
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 7,
        paddingBottom: last ? 0 : 18,
        minWidth: 0
      }
    }, summary ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-regular) var(--fs-14)/1.45 var(--font-sans)',
        color: 'var(--text-secondary)',
        maxWidth: '62ch',
        textWrap: 'pretty'
      }
    }, summary) : null, children));
  }
  function Positions({
    positions
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0,1fr))',
        gap: 24
      }
    }, positions.map((p, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 3,
        minWidth: 0,
        paddingTop: 8,
        borderTop: '1px solid var(--border-hairline)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, p.agent), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-medium) var(--fs-14)/1.3 var(--font-sans)',
        color: 'var(--text-primary)'
      }
    }, p.position), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        textWrap: 'pretty'
      }
    }, p.basis), /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, "confidence ", p.confidence))));
  }
  function Scoring({
    candidates
  }) {
    const top = Math.max.apply(null, candidates.map(o => parseFloat(o.score)));
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column'
      }
    }, candidates.map(o => {
      const chosen = o.verdict === 'chosen';
      return /*#__PURE__*/React.createElement("div", {
        key: o.rank,
        style: {
          display: 'grid',
          gridTemplateColumns: 'minmax(0,1fr) 88px 42px 72px',
          gap: 14,
          alignItems: 'center',
          padding: '8px 0',
          borderTop: '1px solid var(--border-hairline)'
        }
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
          minWidth: 0
        }
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          font: `${chosen ? 'var(--fw-medium)' : 'var(--fw-regular)'} var(--fs-13)/1.35 var(--font-sans)`,
          color: chosen ? 'var(--text-primary)' : 'var(--text-secondary)'
        }
      }, o.name), /*#__PURE__*/React.createElement("span", {
        style: {
          font: 'var(--type-mono)',
          color: 'var(--text-tertiary)'
        }
      }, o.proposedBy)), /*#__PURE__*/React.createElement("span", {
        style: {
          display: 'flex',
          alignItems: 'center',
          height: 2,
          background: 'var(--border-hairline)'
        }
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          width: `${parseFloat(o.score) / top * 100}%`,
          height: 2,
          background: chosen ? 'var(--status-allowed-dot)' : 'var(--text-tertiary)',
          opacity: chosen ? 1 : .45
        }
      })), /*#__PURE__*/React.createElement("span", {
        "data-numeric": true,
        style: {
          font: 'var(--type-mono)',
          fontSize: 'var(--fs-13)',
          color: chosen ? 'var(--text-primary)' : 'var(--text-tertiary)',
          textAlign: 'right'
        }
      }, o.score), /*#__PURE__*/React.createElement("span", {
        style: {
          font: 'var(--type-body-sm)',
          textAlign: 'right',
          color: chosen ? 'var(--status-allowed-fg)' : o.verdict === 'rejected' ? 'var(--status-blocked-fg)' : 'var(--text-tertiary)'
        }
      }, chosen ? 'Chosen' : o.verdict === 'rejected' ? 'Rejected' : 'Considered'));
    }));
  }

  /* THE VERDICT — the page's dominant element. Status word, consequence, authority facts. */
  function Verdict({
    c,
    s
  }) {
    const consequence = c.status === 'blocked' || c.status === 'escalated' ? c.reasons[0].value : c.status === 'failed' ? (c.reasons.find(r => r.label === 'Failure') || c.reasons[0]).value : (c.reasons.find(r => r.label === 'Basis') || c.reasons[0]).value;
    return /*#__PURE__*/React.createElement("section", {
      style: {
        display: 'grid',
        gridTemplateColumns: 'minmax(0,1fr) 232px',
        gap: 40,
        alignItems: 'start',
        padding: '28px 0 30px'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-semibold) 46px/1 var(--font-sans)',
        letterSpacing: '-0.038em',
        color: s.tone
      }
    }, s.verdict), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-regular) 17px/1.45 var(--font-sans)',
        color: 'var(--text-primary)',
        maxWidth: '52ch',
        textWrap: 'pretty'
      }
    }, consequence), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        maxWidth: '56ch',
        textWrap: 'pretty'
      }
    }, s.govern)), /*#__PURE__*/React.createElement("dl", {
      style: {
        margin: 0,
        display: 'grid',
        gridTemplateColumns: 'minmax(0,1fr)',
        rowGap: 12,
        paddingLeft: 22,
        borderLeft: `2px solid ${s.tone}`
      }
    }, [['Policy', c.policy, true], ['Decision', s.decision || s.verdict, false], ['Authority', s.authority, false]].map(([k, v, mono]) => /*#__PURE__*/React.createElement("div", {
      key: k,
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 2
      }
    }, /*#__PURE__*/React.createElement("dt", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, k), /*#__PURE__*/React.createElement("dd", {
      style: {
        margin: 0,
        font: mono ? 'var(--type-mono)' : 'var(--type-body-sm)',
        fontSize: 'var(--fs-13)',
        color: k === 'Authority' ? s.tone : 'var(--text-primary)'
      }
    }, v)))));
  }
  function ExecutorBlock({
    c,
    s
  }) {
    const detail = !c.exec ? c.status === 'blocked' ? `No external call was made because GOVERN denied execution. Nothing reached ${c.surface}.` : 'Execution is withheld while the case is in review. The executor runs only if GOVERN allows it after a fresh evaluation.' : c.exec.result.startsWith('Failed') ? `${c.exec.target} returned ${c.exec.result.replace('Failed · ', '')} after GOVERN authorised the call. No partial state was written, and there is no automatic retry.` : `External action completed after GOVERN authorisation. ${c.exec.result}.`;
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 9
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 4
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-medium) var(--fs-16)/1.3 var(--font-sans)',
        color: s.execTone
      }
    }, s.execLead), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body)',
        color: 'var(--text-secondary)',
        maxWidth: '58ch',
        textWrap: 'pretty'
      }
    }, detail)), c.exec ? /*#__PURE__*/React.createElement(Disclosure, {
      label: "Show execution detail"
    }, /*#__PURE__*/React.createElement("dl", {
      style: {
        margin: 0,
        display: 'grid',
        gridTemplateColumns: '86px minmax(0,1fr)',
        rowGap: 6,
        columnGap: 20,
        maxWidth: 420,
        paddingTop: 8,
        borderTop: '1px solid var(--border-hairline)'
      }
    }, [['Reference', c.exec.id], ['Target', c.exec.target], ['Duration', c.exec.duration], ['At', c.exec.at]].map(([k, v]) => /*#__PURE__*/React.createElement(React.Fragment, {
      key: k
    }, /*#__PURE__*/React.createElement("dt", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, k), /*#__PURE__*/React.createElement("dd", {
      "data-numeric": true,
      style: {
        margin: 0,
        font: 'var(--type-mono)',
        fontSize: 'var(--fs-13)',
        color: 'var(--text-primary)'
      }
    }, v))))) : null);
  }
  const REVIEW_REASON = {
    'CASE-2041': 'Policy blocked a payout that finance may have re-authorised out of band. A reviewer records whether the ceiling is current.',
    'CASE-2043': 'Two agents disagreed on a name match and GOVERN withheld authority rather than guess. A reviewer records what the documents show.',
    'CASE-2044': 'GOVERN authorised the action and the partner failed mid-replay. A reviewer records whether the partner incident is closed.'
  };
  const REVIEW_ASK = {
    'CASE-2041': 'Whether the vendor ceiling in policy payout-v4 is current, and whether this payout was authorised elsewhere.',
    'CASE-2043': 'Whether the submitted documents resolve the name mismatch.',
    'CASE-2044': 'Whether the partner has confirmed recovery.'
  };
  function ReviewSection({
    c,
    onAnnotate,
    onToast
  }) {
    return /*#__PURE__*/React.createElement("section", {
      style: {
        marginTop: 32,
        padding: '18px 0 0 24px',
        borderTop: '1px solid var(--border-subtle)',
        borderLeft: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: 14
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--status-escalated-fg)'
      }
    }, "Human review"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0,1fr))',
        gap: 28
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 5
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-medium) var(--fs-14)/1.35 var(--font-sans)'
      }
    }, "Why a human is here"), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        textWrap: 'pretty'
      }
    }, REVIEW_REASON[c.id])), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 5
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-medium) var(--fs-14)/1.35 var(--font-sans)'
      }
    }, "What the reviewer provides"), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        textWrap: 'pretty'
      }
    }, REVIEW_ASK[c.id]))), /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        gap: 8,
        alignItems: 'flex-start',
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        maxWidth: '64ch',
        textWrap: 'pretty'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "lock",
      size: 13,
      style: {
        color: 'var(--text-tertiary)',
        marginTop: 3
      }
    }), "Review annotations do not rewrite the GOVERN decision and cannot authorise execution."), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      onClick: onAnnotate
    }, "Add annotation"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      onClick: () => onToast('Evidence requested', c.id + ' · recorded in the trail')
    }, "Request more evidence"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      onClick: () => onToast('Policy flagged for owner', 'policy ' + c.policy)
    }, "Flag policy")), c.notes.length ? /*#__PURE__*/React.createElement(Disclosure, {
      label: "Earlier annotations",
      count: c.notes.length
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, c.notes.map((n, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        maxWidth: '64ch'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, n.who, " \xB7 ", n.when), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        textWrap: 'pretty'
      }
    }, n.text))))) : null);
  }
  const EVENT = {
    intake: 'Case opened',
    agents: 'Agent positions received',
    conflict: 'Conflict detected',
    resolve: 'Options resolved',
    weigh: 'Scoring completed',
    govern: 'GOVERN decided',
    executor: 'Executor',
    reviewer: 'Annotation recorded'
  };
  function AuditSection({
    c
  }) {
    const recent = c.audit.slice().reverse().slice(0, 4);
    return /*#__PURE__*/React.createElement("section", {
      style: {
        marginTop: 32,
        paddingTop: 18,
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-secondary)'
      }
    }, "Audit trail"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 5
      }
    }, recent.map((e, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: 'grid',
        gridTemplateColumns: '96px minmax(0,1fr)',
        gap: 20,
        alignItems: 'baseline'
      }
    }, /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-secondary)'
      }
    }, String(e.time).slice(0, 8)), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, e.actor === 'govern' || e.actor === 'executor' ? `${EVENT[e.actor]} — ${e.message.toLowerCase()}` : EVENT[e.actor] || e.message)))), /*#__PURE__*/React.createElement(Disclosure, {
      label: "Show full audit trail",
      count: c.audit.length
    }, /*#__PURE__*/React.createElement(AuditTrail, {
      entries: c.audit
    })));
  }
  function DecisionRecord({
    c,
    onBack,
    onToast
  }) {
    const [dialog, setDialog] = React.useState(false);
    const s = STATE[c.status] || STATE.allowed;
    const chose = c.candidates.find(o => o.verdict === 'chosen') || c.candidates[0];
    const inReview = c.stages.some(st => st.label === 'Review' && st.state === 'active');
    const toast = (title, detail) => onToast({
      tone: 'neutral',
      title,
      detail
    });
    const govMark = c.status === 'blocked' ? 'stop' : c.status === 'escalated' ? 'hold' : 'none';
    return /*#__PURE__*/React.createElement("div", {
      style: {
        overflow: 'auto',
        height: '100%',
        position: 'relative'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 900,
        margin: '0 auto',
        padding: '20px 28px 60px'
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: onBack,
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 7,
        border: 0,
        background: 'none',
        padding: 0,
        marginBottom: 20,
        cursor: 'pointer',
        color: 'var(--text-secondary)',
        font: 'var(--type-body-sm)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "arrow-left",
      size: 13
    }), " Cases"), /*#__PURE__*/React.createElement("header", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 7
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 14
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-secondary)'
      }
    }, c.id), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, c.domain, " \xB7 ", c.value)), /*#__PURE__*/React.createElement("h1", {
      style: {
        font: 'var(--fw-medium) 20px/1.25 var(--font-sans)',
        letterSpacing: '-0.018em',
        color: 'var(--text-primary)',
        maxWidth: '34ch'
      }
    }, c.title)), /*#__PURE__*/React.createElement(Verdict, {
      c: c,
      s: s
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 8,
        paddingBottom: 26,
        borderBottom: '1px solid var(--border-subtle)'
      }
    }, /*#__PURE__*/React.createElement(Button, {
      icon: "message-square-plus",
      onClick: () => setDialog(true)
    }, "Annotate"), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      icon: "refresh-cw",
      onClick: () => toast('Re-evaluation requested', c.id + ' · queued for GOVERN')
    }, "Request re-evaluation")), /*#__PURE__*/React.createElement("div", {
      style: {
        paddingTop: 26
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-block',
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
        paddingBottom: 18
      }
    }, "How Sentinel reached this"), /*#__PURE__*/React.createElement(Stage, {
      label: "Agents",
      summary: `${c.agents} agent${c.agents === 1 ? '' : 's'} proposed a position on this action.`
    }, c.positions.length ? /*#__PURE__*/React.createElement(Disclosure, {
      label: "Show positions",
      count: c.positions.length
    }, /*#__PURE__*/React.createElement(Positions, {
      positions: c.positions
    })) : null), /*#__PURE__*/React.createElement(Stage, {
      label: "Conflict",
      mark: c.positions.length ? 'split' : 'none',
      summary: c.positions.length ? `Disagreed on ${c.conflictSubject.charAt(0).toLowerCase() + c.conflictSubject.slice(1)}.` : 'No disagreement — the agents returned the same position.'
    }), /*#__PURE__*/React.createElement(Stage, {
      label: "Resolve",
      summary: c.candidates.length === 1 ? 'A single viable option remained.' : `Reconciled into ${c.candidates.length} mutually exclusive options.`
    }), /*#__PURE__*/React.createElement(Stage, {
      label: "Weigh",
      summary: `“${chose.name}” scored highest at ${chose.score}.`
    }, /*#__PURE__*/React.createElement(Disclosure, {
      label: "Show scoring",
      count: c.candidates.length
    }, /*#__PURE__*/React.createElement(Scoring, {
      candidates: c.candidates
    }))), /*#__PURE__*/React.createElement(Stage, {
      label: "Govern",
      mark: govMark,
      summary: `Evaluated “${chose.name}” against policy ${c.policy}.`
    }, /*#__PURE__*/React.createElement(Disclosure, {
      label: "Show governance reasoning"
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 9,
        maxWidth: '64ch'
      }
    }, c.reasons.map((r, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: 'grid',
        gridTemplateColumns: '86px minmax(0,1fr)',
        gap: 20,
        paddingTop: 8,
        borderTop: '1px solid var(--border-hairline)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, r.label), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        textWrap: 'pretty'
      }
    }, r.value))), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, "decided by GOVERN \xB7 ", c.opened, " \xB7 ", c.latency, " end to end")))), /*#__PURE__*/React.createElement(Stage, {
      label: "Executor",
      last: true,
      mark: c.exec && c.exec.result.startsWith('Failed') ? 'stop' : 'none'
    }, /*#__PURE__*/React.createElement(ExecutorBlock, {
      c: c,
      s: s
    }))), inReview ? /*#__PURE__*/React.createElement(ReviewSection, {
      c: c,
      onAnnotate: () => setDialog(true),
      onToast: toast
    }) : null, /*#__PURE__*/React.createElement(AuditSection, {
      c: c
    })), /*#__PURE__*/React.createElement(Dialog, {
      open: dialog,
      label: "Human review",
      title: "Add annotation",
      description: "Appended to the audit trail. It does not change the GOVERN decision.",
      onClose: () => setDialog(false),
      footer: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
        onClick: () => setDialog(false)
      }, "Cancel"), /*#__PURE__*/React.createElement(Button, {
        variant: "primary",
        onClick: () => {
          setDialog(false);
          toast('Annotation recorded', c.id + ' · audit trail updated');
        }
      }, "Record note"))
    }, /*#__PURE__*/React.createElement(Textarea, {
      rows: 4,
      placeholder: "What should a future reviewer know?",
      counter: "0/500"
    })));
  }
  Object.assign(window, {
    DecisionRecord
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/DecisionRecord.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Overview.jsx
try { (() => {
(() => {
  const {
    Block,
    Signal,
    ChainBand,
    Outcome
  } = window;
  function AttentionItem({
    c,
    onOpen,
    last
  }) {
    const [hover, setHover] = React.useState(false);
    return /*#__PURE__*/React.createElement("div", {
      onClick: () => onOpen(c.id),
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
      style: {
        display: 'grid',
        gridTemplateColumns: '108px minmax(0,1fr) 200px 96px',
        gap: 20,
        alignItems: 'baseline',
        padding: '16px 8px 16px 0',
        cursor: 'pointer',
        borderBottom: last ? 0 : '1px solid var(--border-hairline)',
        background: hover ? 'var(--bg-hover)' : 'transparent',
        transition: 'var(--transition-control)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, c.id), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-medium) var(--fs-15)/1.3 var(--font-sans)',
        letterSpacing: '-0.008em'
      }
    }, c.title), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        textWrap: 'pretty'
      }
    }, c.shortReason)), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-tertiary)'
      }
    }, c.domain, " \xB7 ", c.value), /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        justifyContent: 'flex-end'
      }
    }, /*#__PURE__*/React.createElement(Outcome, {
      status: c.status
    })));
  }
  function Overview({
    cases,
    onOpen,
    onGo
  }) {
    const attention = cases.filter(c => ['blocked', 'escalated', 'failed'].includes(c.status));
    return /*#__PURE__*/React.createElement("div", {
      style: {
        overflow: 'auto',
        height: '100%'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1080,
        margin: '0 auto',
        padding: '56px 28px 72px',
        display: 'flex',
        flexDirection: 'column',
        gap: 54
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, "Last 24 hours"), /*#__PURE__*/React.createElement("h1", {
      style: {
        font: 'var(--fw-semibold) 30px/1.2 var(--font-sans)',
        letterSpacing: '-0.026em',
        maxWidth: '24ch'
      }
    }, "Sentinel governed 412 automated actions. Three stopped."), /*#__PURE__*/React.createElement("p", {
      style: {
        font: 'var(--type-body)',
        color: 'var(--text-secondary)',
        maxWidth: '62ch',
        textWrap: 'pretty'
      }
    }, "396 executed as decided. Twelve were blocked by policy, four escalated for review, two failed downstream. Nothing executed without a GOVERN decision.")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'grid',
        gridTemplateColumns: 'repeat(4, minmax(0,1fr))',
        gap: 32
      }
    }, /*#__PURE__*/React.createElement(Signal, {
      label: "Execution",
      value: "99.4%",
      note: "396 of 398 calls succeeded",
      state: "allowed"
    }), /*#__PURE__*/React.createElement(Signal, {
      label: "Governance latency",
      value: "118ms",
      note: "p99, budget 150ms",
      state: "escalated"
    }), /*#__PURE__*/React.createElement(Signal, {
      label: "Agent conflict",
      value: "9.2%",
      note: "38 cases needed RESOLVE",
      state: "escalated"
    }), /*#__PURE__*/React.createElement(Signal, {
      label: "Audit completeness",
      value: "100%",
      note: "no gaps in 30 days",
      state: "allowed"
    })), /*#__PURE__*/React.createElement(Block, {
      eyebrow: "Needs attention",
      title: attention.length + ' cases the system could not close',
      actions: /*#__PURE__*/React.createElement("button", {
        type: "button",
        onClick: () => onGo('cases'),
        style: {
          border: 0,
          background: 'none',
          cursor: 'pointer',
          color: 'var(--text-secondary)',
          font: 'var(--type-body-sm)'
        }
      }, "All cases \u2192")
    }, /*#__PURE__*/React.createElement("div", null, attention.map((c, i) => /*#__PURE__*/React.createElement(AttentionItem, {
      key: c.id,
      c: c,
      onOpen: onOpen,
      last: i === attention.length - 1
    })))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 16
      }
    }, /*#__PURE__*/React.createElement(ChainBand, {
      marks: {
        conflict: 'split',
        govern: 'stop'
      },
      note: "Every action crosses these six stages. Today 38 split at CONFLICT and 16 stopped at GOVERN."
    }), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onGo('scenario'),
      style: {
        alignSelf: 'flex-start',
        border: 0,
        background: 'none',
        padding: 0,
        cursor: 'pointer',
        color: 'var(--text-secondary)',
        font: 'var(--type-body-sm)'
      }
    }, "Walk a case through the chain \u2192"))));
  }
  Object.assign(window, {
    Overview
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Overview.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Primitives.jsx
try { (() => {
(() => {
  const {
    Icon
  } = window.SentinelDesignSystem_8a81b0;

  /* Typographic grouping: an eyebrow, a rule, and space. No card, no border box. */
  function Block({
    eyebrow,
    title,
    meta,
    actions,
    children,
    gap = 14,
    style
  }) {
    return /*#__PURE__*/React.createElement("section", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap,
        minWidth: 0,
        ...style
      }
    }, eyebrow || title || actions ? /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'baseline',
        gap: 12,
        paddingBottom: 9,
        borderBottom: '1px solid var(--border-hairline)'
      }
    }, eyebrow ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, eyebrow) : null, title ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-medium) var(--fs-14)/1.3 var(--font-sans)'
      }
    }, title) : null, meta ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, meta) : null, /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), actions) : null, children);
  }

  /* One operational signal: a word, a number, a state. No box. */
  function Signal({
    label,
    value,
    state = 'allowed',
    note
  }) {
    const dot = {
      allowed: 'var(--status-allowed-dot)',
      escalated: 'var(--status-escalated-dot)',
      blocked: 'var(--status-blocked-dot)',
      neutral: 'var(--text-tertiary)'
    }[state];
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 7
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 5,
        height: 5,
        borderRadius: 99,
        background: dot,
        flex: '0 0 auto'
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, label)), /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--fw-medium) 19px/1 var(--font-mono)',
        color: 'var(--text-primary)'
      }
    }, value), note ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-caption)',
        color: 'var(--text-tertiary)'
      }
    }, note) : null);
  }

  /* Progressive disclosure: level 3 opens in place, closed by default. */
  function Disclosure({
    label,
    count,
    children,
    defaultOpen = false
  }) {
    const [open, setOpen] = React.useState(defaultOpen);
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: open ? 16 : 0
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => setOpen(!open),
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 7,
        alignSelf: 'flex-start',
        padding: '4px 0',
        border: 0,
        background: 'none',
        cursor: 'pointer',
        color: 'var(--text-secondary)',
        font: 'var(--type-body-sm)',
        transition: 'var(--transition-control)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: open ? 'chevron-down' : 'chevron-right',
      size: 13,
      style: {
        color: 'var(--text-tertiary)'
      }
    }), label, count != null ? /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, count) : null), open ? children : null);
  }

  /* Outcome as a word, not a pill. */
  function Outcome({
    status,
    size = 'md'
  }) {
    const map = {
      allowed: ['Executed', 'var(--status-allowed-fg)'],
      blocked: ['Blocked', 'var(--status-blocked-fg)'],
      escalated: ['Escalated', 'var(--status-escalated-fg)'],
      failed: ['Failed', '#D96B6B', 'var(--fs-16)'],
      conflict: ['Conflict', 'var(--status-conflict-fg)'],
      pending: ['Pending', 'var(--status-pending-fg)'],
      review: ['In review', 'var(--text-secondary)']
    };
    const entry = map[status] || map.pending;
    return /*#__PURE__*/React.createElement("span", {
      style: {
        font: `var(--fw-semibold) ${size === 'lg' ? 'var(--fs-16)' : entry[2] || 'var(--fs-15)'}/1.2 var(--font-sans)`,
        color: entry[1]
      }
    }, entry[0]);
  }
  function Sparkline({
    points = [],
    tone = 'neutral',
    height = 24
  }) {
    const max = Math.max.apply(null, points.concat([1]));
    const color = tone === 'blocked' ? 'var(--status-blocked-dot)' : tone === 'escalated' ? 'var(--status-escalated-dot)' : tone === 'allowed' ? 'var(--status-allowed-dot)' : 'var(--text-tertiary)';
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'flex-end',
        gap: 3,
        height
      }
    }, points.map((p, i) => /*#__PURE__*/React.createElement("span", {
      key: i,
      style: {
        width: 5,
        flex: '0 0 auto',
        height: Math.max(2, p / max * height),
        background: color,
        opacity: i === points.length - 1 ? 1 : 0.4
      }
    })));
  }

  /* The signature chain as a quiet band of stage names. Used sparingly, never per row. */
  function ChainBand({
    marks = {},
    note
  }) {
    const LINKS = ['Agents', 'Conflict', 'Resolve', 'Weigh', 'Govern', 'Executor'];
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center'
      }
    }, LINKS.map((l, i) => {
      const m = marks[l.toLowerCase()];
      const color = m === 'stop' ? '#37773E' : m === 'hold' ? 'var(--status-escalated-fg)' : m === 'split' ? 'var(--status-conflict-fg)' : 'var(--text-tertiary)';
      return /*#__PURE__*/React.createElement(React.Fragment, {
        key: l
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          font: 'var(--type-label)',
          letterSpacing: 'var(--ls-label)',
          textTransform: 'uppercase',
          color,
          whiteSpace: 'nowrap'
        }
      }, l), i < LINKS.length - 1 ? /*#__PURE__*/React.createElement("span", {
        style: {
          flex: 1,
          height: 1,
          minWidth: 12,
          margin: '0 10px',
          background: 'var(--border-subtle)'
        }
      }) : null);
    })), note ? /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-caption)',
        color: 'var(--text-tertiary)'
      }
    }, note) : null);
  }
  Object.assign(window, {
    Block,
    Signal,
    Disclosure,
    Outcome,
    Sparkline,
    ChainBand
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Primitives.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Reliability.jsx
try { (() => {
(() => {
  const {
    Icon
  } = window.SentinelDesignSystem_8a81b0;
  const {
    Signal,
    Sparkline,
    Block
  } = window;
  const LATENCY = [62, 71, 68, 79, 74, 88, 84, 96, 91, 104, 99, 112, 108, 118, 116];
  function Reliability({
    executors,
    cases
  }) {
    const failed = cases.filter(c => c.status === 'failed');
    return /*#__PURE__*/React.createElement("div", {
      style: {
        overflow: 'auto',
        height: '100%'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1000,
        margin: '0 auto',
        padding: '44px 28px 80px',
        display: 'flex',
        flexDirection: 'column',
        gap: 46
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)',
        letterSpacing: '-0.022em'
      }
    }, "Reliability"), /*#__PURE__*/React.createElement("p", {
      style: {
        font: 'var(--type-body)',
        color: 'var(--text-secondary)',
        maxWidth: '62ch',
        textWrap: 'pretty'
      }
    }, "The control plane is trustworthy right now. Governance latency is inside budget but climbing, and both execution failures today came from one region.")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'grid',
        gridTemplateColumns: 'repeat(4, minmax(0,1fr))',
        gap: 32
      }
    }, /*#__PURE__*/React.createElement(Signal, {
      label: "Execution success",
      value: "99.4%",
      note: "2 failures in 398 calls",
      state: "allowed"
    }), /*#__PURE__*/React.createElement(Signal, {
      label: "Governance latency",
      value: "118ms",
      note: "p99 of a 150ms budget",
      state: "escalated"
    }), /*#__PURE__*/React.createElement(Signal, {
      label: "Agent agreement",
      value: "90.8%",
      note: "38 conflicts resolved",
      state: "allowed"
    }), /*#__PURE__*/React.createElement(Signal, {
      label: "Audit completeness",
      value: "100%",
      note: "verified hourly, 30d",
      state: "allowed"
    })), /*#__PURE__*/React.createElement(Block, {
      eyebrow: "Governance latency",
      title: "p99 over the last 3 hours",
      meta: "budget 150ms"
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'flex-end',
        gap: 16
      }
    }, /*#__PURE__*/React.createElement(Sparkline, {
      points: LATENCY,
      tone: "escalated",
      height: 56
    }), /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--fw-medium) 17px/1 var(--font-mono)',
        color: 'var(--status-escalated-fg)'
      }
    }, "118ms")), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-caption)',
        color: 'var(--text-tertiary)'
      }
    }, "Rising with conflict volume \u2014 RESOLVE runs on every disagreement.")), /*#__PURE__*/React.createElement(Block, {
      eyebrow: "Workers",
      title: "Execution capacity"
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column'
      }
    }, executors.map((e, i) => /*#__PURE__*/React.createElement("div", {
      key: e.region,
      style: {
        display: 'grid',
        gridTemplateColumns: 'minmax(0,1fr) 90px 90px 140px',
        gap: 20,
        alignItems: 'baseline',
        padding: '13px 0',
        borderBottom: i === executors.length - 1 ? 0 : '1px solid var(--border-hairline)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)'
      }
    }, e.region), /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, "queue ", e.depth), /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, e.last), /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 7,
        font: 'var(--type-body-sm)',
        color: e.state === 'allowed' ? 'var(--text-secondary)' : 'var(--status-escalated-fg)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 5,
        height: 5,
        borderRadius: 99,
        background: e.state === 'allowed' ? 'var(--status-allowed-dot)' : 'var(--status-escalated-dot)'
      }
    }), e.note)))), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-caption)',
        color: 'var(--text-tertiary)'
      }
    }, "Queue depth above 5 raises an escalation, never a block.")), /*#__PURE__*/React.createElement(Block, {
      eyebrow: "Failures",
      title: "Execution failures today",
      meta: String(failed.length)
    }, failed.map(c => /*#__PURE__*/React.createElement("div", {
      key: c.id,
      style: {
        display: 'grid',
        gridTemplateColumns: '108px minmax(0,1fr) 200px',
        gap: 20,
        alignItems: 'baseline',
        padding: '4px 0'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, c.id), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        textWrap: 'pretty'
      }
    }, c.title, " \u2014 ", c.reasons[1].value), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--status-blocked-fg)'
      }
    }, "us-east-1 \xB7 HTTP 503"))), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-caption)',
        color: 'var(--text-tertiary)'
      }
    }, "A failed execution never retries without a fresh GOVERN decision."))));
  }
  Object.assign(window, {
    Reliability
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Reliability.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Review.jsx
try { (() => {
(() => {
  const {
    Button,
    Textarea,
    Checkbox,
    Icon
  } = window.SentinelDesignSystem_8a81b0;
  const {
    Outcome,
    Disclosure
  } = window;
  const WHY = {
    'CASE-2041': 'Policy blocked a payout that finance may have re-authorised out of band. A reviewer records whether the ceiling is stale.',
    'CASE-2043': 'Two agents disagreed on a name match and GOVERN escalated rather than guess. A reviewer records what the documents actually show.',
    'CASE-2044': 'GOVERN allowed the action; the partner failed mid-replay. A reviewer records whether the partner incident is closed.'
  };
  const ASK = {
    'CASE-2041': ['Is the vendor ceiling in policy payout-v4 current?', 'Was this payout authorised elsewhere?'],
    'CASE-2043': ['Do the submitted documents resolve the name mismatch?', 'Should the match tolerance be revisited?'],
    'CASE-2044': ['Has the partner confirmed recovery?', 'Is a fresh evaluation appropriate now?']
  };
  function Review({
    cases,
    onOpen,
    onToast
  }) {
    const queue = cases.filter(c => c.stages.some(s => s.label === 'Review' && s.state === 'active'));
    const [sel, setSel] = React.useState(queue[0] ? queue[0].id : null);
    const [note, setNote] = React.useState('');
    const c = queue.find(q => q.id === sel) || queue[0];
    return /*#__PURE__*/React.createElement("div", {
      style: {
        overflow: 'auto',
        height: '100%'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1000,
        margin: '0 auto',
        padding: '44px 28px 80px',
        display: 'flex',
        flexDirection: 'column',
        gap: 34
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)',
        letterSpacing: '-0.022em'
      }
    }, "Human review"), /*#__PURE__*/React.createElement("p", {
      style: {
        font: 'var(--type-body)',
        color: 'var(--text-secondary)',
        maxWidth: '62ch'
      }
    }, queue.length, " cases are waiting for context from a person. Sentinel has already decided each one \u2014 review records what a decision could not know.")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 24,
        borderBottom: '1px solid var(--border-hairline)'
      }
    }, queue.map(q => {
      const active = c && q.id === c.id;
      return /*#__PURE__*/React.createElement("button", {
        key: q.id,
        type: "button",
        onClick: () => setSel(q.id),
        style: {
          position: 'relative',
          display: 'inline-flex',
          alignItems: 'baseline',
          gap: 8,
          height: 34,
          border: 0,
          background: 'none',
          padding: 0,
          cursor: 'pointer',
          color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
          font: 'var(--type-mono)',
          transition: 'var(--transition-control)'
        }
      }, q.id, /*#__PURE__*/React.createElement("span", {
        style: {
          font: 'var(--fw-regular) var(--fs-12)/1 var(--font-sans)'
        }
      }, q.notes.length, " note", q.notes.length === 1 ? '' : 's'), /*#__PURE__*/React.createElement("span", {
        style: {
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: -1,
          height: 1,
          background: active ? 'var(--text-primary)' : 'transparent'
        }
      }));
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 14
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, c.domain, " \xB7 ", c.value), /*#__PURE__*/React.createElement(Outcome, {
      status: c.status
    })), /*#__PURE__*/React.createElement("h2", {
      style: {
        font: 'var(--fw-semibold) 22px/1.25 var(--font-sans)',
        letterSpacing: '-0.02em',
        maxWidth: '30ch'
      }
    }, c.title), /*#__PURE__*/React.createElement("p", {
      style: {
        font: 'var(--fw-regular) var(--fs-16)/1.5 var(--font-sans)',
        color: 'var(--text-secondary)',
        maxWidth: '64ch',
        textWrap: 'pretty'
      }
    }, WHY[c.id])), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'grid',
        gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)',
        gap: 40
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, "Sentinel already decided"), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body)',
        textWrap: 'pretty'
      }
    }, c.headline), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, "policy ", c.policy, " \xB7 decided by GOVERN"), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onOpen(c.id),
      style: {
        alignSelf: 'flex-start',
        border: 0,
        background: 'none',
        padding: 0,
        cursor: 'pointer',
        color: 'var(--text-secondary)',
        font: 'var(--type-body-sm)'
      }
    }, "See the reasoning \u2192")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, "You are asked to confirm"), (ASK[c.id] || []).map((q, i) => /*#__PURE__*/React.createElement("span", {
      key: i,
      style: {
        display: 'flex',
        gap: 9,
        font: 'var(--type-body)',
        textWrap: 'pretty'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: 'var(--text-tertiary)'
      }
    }, i + 1), q)))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        paddingTop: 22,
        borderTop: '1px solid var(--border-subtle)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "lock",
      size: 13,
      style: {
        color: 'var(--text-tertiary)'
      }
    }), "Review annotates. It cannot allow, block, override or retry \u2014 GOVERN keeps that authority."), /*#__PURE__*/React.createElement(Textarea, {
      rows: 5,
      value: note,
      onChange: e => setNote(e.target.value),
      placeholder: "What should a future reviewer or policy owner know?",
      counter: `${note.length}/500`
    }), /*#__PURE__*/React.createElement(Checkbox, {
      label: "Flag the governing policy for owner review",
      description: `policy ${c.policy} · routed to the policy owner, not the executor`
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 10
      }
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      onClick: () => {
        setNote('');
        onToast();
      }
    }, "Record note"), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost"
    }, "Discard")), c.notes.length ? /*#__PURE__*/React.createElement(Disclosure, {
      label: "Earlier notes",
      count: c.notes.length
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }
    }, c.notes.map((n, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 3,
        maxWidth: '68ch'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, n.who, " \xB7 ", n.when), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        textWrap: 'pretty'
      }
    }, n.text))))) : null)));
  }
  Object.assign(window, {
    Review
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Review.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Scenario.jsx
try { (() => {
(() => {
  const {
    CausalChain,
    Button,
    IconButton,
    StatusBadge,
    InlineNotice,
    Icon,
    Badge
  } = window.SentinelDesignSystem_8a81b0;
  const {
    Block
  } = window;
  function Scenario({
    steps,
    onOpen
  }) {
    const [i, setI] = React.useState(0);
    const step = steps[i];
    const last = i === steps.length - 1;
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'grid',
        gridTemplateColumns: 'minmax(0,1fr) 400px',
        height: '100%',
        minHeight: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        padding: '24px 24px 40px',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
        overflow: 'auto'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 6
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)'
      }
    }, "Scenario"), /*#__PURE__*/React.createElement("h1", {
      style: {
        font: 'var(--fw-semibold) 24px/1.15 var(--font-sans)',
        letterSpacing: '-0.022em'
      }
    }, "Walk one case through the chain"), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        maxWidth: '72ch'
      }
    }, "A \u20B918,40,000 vendor payout, replayed step by step \u2014 what each link did, and where the action stopped.")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 18,
        paddingTop: 8,
        borderTop: '1px solid var(--border-subtle)'
      }
    }, /*#__PURE__*/React.createElement(CausalChain, {
      states: step.chain,
      detail: `t+${step.t}`,
      style: {
        minWidth: 620
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 9
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-label)',
        letterSpacing: 'var(--ls-label)',
        textTransform: 'uppercase',
        color: 'var(--accent)'
      }
    }, step.link), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, "step ", i + 1, " of ", steps.length)), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-semibold) 18px/1.3 var(--font-sans)',
        letterSpacing: 'var(--ls-heading)'
      }
    }, step.title), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-body)',
        color: 'var(--text-secondary)',
        maxWidth: '70ch',
        textWrap: 'pretty'
      }
    }, step.body)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement(Button, {
      icon: "chevron-left",
      disabled: i === 0,
      onClick: () => setI(Math.max(0, i - 1))
    }, "Back"), last ? /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      trailingIcon: "arrow-up-right",
      onClick: () => onOpen('CASE-2041')
    }, "Open the decision record") : /*#__PURE__*/React.createElement(Button, {
      variant: "primary",
      onClick: () => setI(i + 1)
    }, "Next >"), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      icon: "rotate-ccw",
      onClick: () => setI(0)
    }, "Restart"))), last ? /*#__PURE__*/React.createElement(InlineNotice, {
      tone: "blocked",
      title: "Nothing executed"
    }, "The executor was never called. This is the product's whole point: the chain stops at GOVERN, the reasons are recorded, and a human annotates rather than overrides.") : null), /*#__PURE__*/React.createElement("aside", {
      style: {
        borderLeft: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)',
        padding: '20px',
        overflow: 'auto'
      }
    }, /*#__PURE__*/React.createElement(Block, {
      eyebrow: "Timeline",
      title: "Chain replay"
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column'
      }
    }, steps.map((s, idx) => {
      const active = idx === i;
      const done = idx < i;
      return /*#__PURE__*/React.createElement("button", {
        key: s.link + idx,
        type: "button",
        onClick: () => setI(idx),
        style: {
          display: 'grid',
          gridTemplateColumns: '54px 12px minmax(0,1fr)',
          gap: 10,
          alignItems: 'start',
          textAlign: 'left',
          padding: '11px 8px',
          border: 0,
          borderBottom: '1px solid var(--border-hairline)',
          cursor: 'pointer',
          background: active ? 'var(--bg-selected)' : 'transparent',
          transition: 'var(--transition-control)'
        }
      }, /*#__PURE__*/React.createElement("span", {
        "data-numeric": true,
        style: {
          font: 'var(--type-mono)',
          color: 'var(--text-tertiary)'
        }
      }, s.t), /*#__PURE__*/React.createElement("span", {
        style: {
          display: 'flex',
          justifyContent: 'center',
          paddingTop: 4
        }
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          width: 6,
          height: 6,
          borderRadius: 99,
          background: active ? 'var(--accent)' : done ? 'var(--status-allowed-dot)' : 'transparent',
          border: active || done ? 'none' : '1px solid var(--border-strong)',
          boxShadow: active ? 'var(--glow-accent)' : 'none'
        }
      })), /*#__PURE__*/React.createElement("span", {
        style: {
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          minWidth: 0
        }
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          font: 'var(--type-label)',
          letterSpacing: 'var(--ls-label)',
          textTransform: 'uppercase',
          color: active ? 'var(--text-primary)' : 'var(--text-tertiary)'
        }
      }, s.link), /*#__PURE__*/React.createElement("span", {
        style: {
          font: 'var(--fw-regular) var(--fs-13)/1.35 var(--font-sans)',
          color: active ? 'var(--text-primary)' : 'var(--text-secondary)'
        }
      }, s.title)));
    })))));
  }
  Object.assign(window, {
    Scenario
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Scenario.jsx", error: String((e && e.message) || e) }); }

// ui_kits/control_plane/Shell.jsx
try { (() => {
(() => {
  const {
    Icon
  } = window.SentinelDesignSystem_8a81b0;
  const SURFACES = [{
    value: 'overview',
    label: 'Control plane'
  }, {
    value: 'cases',
    label: 'Cases'
  }, {
    value: 'review',
    label: 'Human review'
  }, {
    value: 'reliability',
    label: 'Reliability'
  }, {
    value: 'audit',
    label: 'Audit'
  }, {
    value: 'scenario',
    label: 'Scenario'
  }];
  function SurfaceLink({
    item,
    active,
    count,
    onSelect
  }) {
    const [hover, setHover] = React.useState(false);
    return /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onSelect(item.value),
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
      style: {
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        height: 40,
        padding: '0 2px',
        border: 0,
        background: 'none',
        cursor: 'pointer',
        color: active ? 'var(--text-primary)' : hover ? 'var(--text-secondary)' : 'var(--text-tertiary)',
        font: 'var(--fw-medium) var(--fs-13)/1 var(--font-sans)',
        letterSpacing: 'var(--ls-body)',
        whiteSpace: 'nowrap',
        transition: 'var(--transition-control)'
      }
    }, item.label, count ? /*#__PURE__*/React.createElement("span", {
      "data-numeric": true,
      style: {
        font: 'var(--type-mono)',
        color: active ? 'var(--text-tertiary)' : 'inherit'
      }
    }, count) : null, /*#__PURE__*/React.createElement("span", {
      style: {
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        height: 1,
        background: active ? 'var(--text-primary)' : 'transparent'
      }
    }));
  }
  function CommandBar({
    view,
    onSelect,
    counts,
    attention
  }) {
    return /*#__PURE__*/React.createElement("header", {
      style: {
        flex: '0 0 auto',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--bg-app)'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 26,
        padding: '0 28px',
        minWidth: 940
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: 9,
        paddingRight: 8
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--fw-semibold) 14px/1 var(--font-sans)',
        letterSpacing: '-0.02em'
      }
    }, "Sentinel"), /*#__PURE__*/React.createElement("span", {
      style: {
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, "production")), /*#__PURE__*/React.createElement("nav", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 22,
        minWidth: 0
      }
    }, SURFACES.map(s => /*#__PURE__*/React.createElement(SurfaceLink, {
      key: s.value,
      item: s,
      active: view === s.value,
      count: counts[s.value],
      onSelect: onSelect
    }))), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), attention ? /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 7,
        font: 'var(--type-body-sm)',
        color: 'var(--text-secondary)',
        whiteSpace: 'nowrap'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 5,
        height: 5,
        borderRadius: 99,
        background: 'var(--status-escalated-dot)'
      }
    }), attention, " need attention") : null, /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        font: 'var(--type-mono)',
        color: 'var(--text-tertiary)'
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "search",
      size: 12
    }), "\u2318K")));
  }
  Object.assign(window, {
    CommandBar,
    SURFACES
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/control_plane/Shell.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.InlineNotice = __ds_scope.InlineNotice;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Textarea = __ds_scope.Textarea;

__ds_ns.AgentDisagreement = __ds_scope.AgentDisagreement;

__ds_ns.AuditTrail = __ds_scope.AuditTrail;

__ds_ns.CandidateOption = __ds_scope.CandidateOption;

__ds_ns.CaseRow = __ds_scope.CaseRow;

__ds_ns.DecisionSummary = __ds_scope.DecisionSummary;

__ds_ns.PipelineTrack = __ds_scope.PipelineTrack;

__ds_ns.SideNav = __ds_scope.SideNav;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.CausalChain = __ds_scope.CausalChain;

__ds_ns.ReliabilityMeter = __ds_scope.ReliabilityMeter;

__ds_ns.SeverityDot = __ds_scope.SeverityDot;

__ds_ns.StatusBadge = __ds_scope.StatusBadge;

__ds_ns.KeyValue = __ds_scope.KeyValue;

__ds_ns.Panel = __ds_scope.Panel;

__ds_ns.SectionHeader = __ds_scope.SectionHeader;

})();
