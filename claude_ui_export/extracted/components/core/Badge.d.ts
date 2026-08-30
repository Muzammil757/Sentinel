import * as React from 'react';
export interface BadgeProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'style'> {
  tone?: 'neutral' | 'accent' | 'allowed' | 'escalated' | 'blocked' | 'conflict';
  /** Mono + uppercase treatment for codes and machine values. */
  mono?: boolean;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}
export declare function Badge(props: BadgeProps): JSX.Element;
