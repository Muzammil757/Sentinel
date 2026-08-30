import * as React from 'react';
/**
 * Governance outcome marker. The status vocabulary is fixed — never invent new outcomes.
 * @startingPoint section="Status" subtitle="Outcome badges, severity dots and reliability meters" viewport="700x200"
 */
export interface StatusBadgeProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'style'> {
  status?: 'allowed' | 'blocked' | 'escalated' | 'failed' | 'conflict' | 'pending' | 'review';
  showIcon?: boolean;
  size?: 'md' | 'lg';
  /** Overrides the default label; keep it one or two words. */
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function StatusBadge(props: StatusBadgeProps): JSX.Element;
