import * as React from 'react';
export type ChainState = 'idle' | 'clear' | 'passed' | 'active' | 'conflict' | 'blocked' | 'escalated' | 'halted';
/** State of each link, keyed by lowercase link name: agents, conflict, resolve, weigh, govern, executor. */
export interface CausalChainStates {
  agents?: ChainState; conflict?: ChainState; resolve?: ChainState;
  weigh?: ChainState; govern?: ChainState; executor?: ChainState;
}
export interface CausalChainProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
  states?: CausalChainStates;
  size?: 'sm' | 'md';
  showLabels?: boolean;
  /** Trailing mono annotation, e.g. "halted at GOVERN · 3.2s". */
  detail?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function CausalChain(props: CausalChainProps): JSX.Element;
