import * as React from 'react';
export interface DecisionReason { label: React.ReactNode; value: React.ReactNode }
export interface DecisionSummaryProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
  outcome?: 'allowed' | 'blocked' | 'escalated' | 'failed';
  /** One sentence stating what GOVERN did. */
  headline: React.ReactNode;
  policy?: React.ReactNode;
  reasons?: DecisionReason[];
  decidedAt?: React.ReactNode;
  /** Always a system authority — never a person. */
  decidedBy?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function DecisionSummary(props: DecisionSummaryProps): JSX.Element;
