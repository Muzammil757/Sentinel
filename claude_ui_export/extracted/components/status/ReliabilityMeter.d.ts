import * as React from 'react';
export interface ReliabilityMeterProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
  label: React.ReactNode;
  /** 0–100. */
  value: number;
  /** Small caption under the bars, e.g. "target 99.5% · 30d". */
  target?: React.ReactNode;
  unit?: string;
  bars?: number;
  tone?: 'allowed' | 'escalated' | 'blocked';
  style?: React.CSSProperties;
}
export declare function ReliabilityMeter(props: ReliabilityMeterProps): JSX.Element;
