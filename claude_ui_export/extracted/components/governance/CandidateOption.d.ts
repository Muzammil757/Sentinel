import * as React from 'react';
export interface CandidateOptionProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
  name: React.ReactNode;
  /** Agent that proposed this option, e.g. "risk-agent v7". */
  proposedBy?: React.ReactNode;
  /** WEIGH score, shown mono and tabular. */
  score?: React.ReactNode;
  verdict?: 'chosen' | 'rejected' | 'considered';
  rationale?: React.ReactNode;
  rank?: React.ReactNode;
  selected?: boolean;
  style?: React.CSSProperties;
}
export declare function CandidateOption(props: CandidateOptionProps): JSX.Element;
