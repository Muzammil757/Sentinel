import * as React from 'react';
export interface CaseRowProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style' | 'id'> {
  /** Mono case identifier, e.g. "CASE-2041". */
  id: React.ReactNode;
  title: React.ReactNode;
  status: 'allowed' | 'blocked' | 'escalated' | 'failed' | 'conflict' | 'pending' | 'review';
  /** Marks that agents disagreed on this case. */
  agentConflict?: boolean;
  /** Where the action would execute, e.g. "Payouts API". */
  surface?: React.ReactNode;
  amount?: React.ReactNode;
  time?: React.ReactNode;
  selected?: boolean;
  style?: React.CSSProperties;
}
export declare function CaseRow(props: CaseRowProps): JSX.Element;
