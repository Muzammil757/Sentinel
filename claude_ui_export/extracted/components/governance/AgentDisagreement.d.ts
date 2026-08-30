import * as React from 'react';
export interface AgentPosition {
  agent: React.ReactNode;
  position: React.ReactNode;
  basis?: React.ReactNode;
  confidence?: React.ReactNode;
}
export interface AgentDisagreementProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
  positions: AgentPosition[];
  /** One line naming what the agents disagree about. */
  subject?: React.ReactNode;
  /** The authority that settled it — GOVERN, or a policy rule. */
  resolvedBy?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function AgentDisagreement(props: AgentDisagreementProps): JSX.Element;
