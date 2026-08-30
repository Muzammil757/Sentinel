import * as React from 'react';
export interface SeverityDotProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'style'> {
  status?: 'allowed' | 'blocked' | 'escalated' | 'failed' | 'conflict' | 'pending';
  label?: React.ReactNode;
  /** Adds a soft halo — reserve for live/attention states. */
  pulse?: boolean;
  size?: number;
  style?: React.CSSProperties;
}
export declare function SeverityDot(props: SeverityDotProps): JSX.Element;
