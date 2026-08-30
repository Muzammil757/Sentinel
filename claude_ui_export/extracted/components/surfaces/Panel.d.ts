import * as React from 'react';
/**
 * Bordered content region — Sentinel's only container. No drop shadows, no nesting beyond one level.
 * @startingPoint section="Surfaces" subtitle="Panels, section headers and key/value readouts" viewport="700x300"
 */
export interface PanelProps extends Omit<React.HTMLAttributes<HTMLElement>, 'style' | 'title'> {
  title?: React.ReactNode;
  /** Mono uppercase eyebrow shown before the title. */
  label?: React.ReactNode;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  padded?: boolean;
  tone?: 'surface' | 'inset' | 'console';
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
  children?: React.ReactNode;
}
export declare function Panel(props: PanelProps): JSX.Element;
