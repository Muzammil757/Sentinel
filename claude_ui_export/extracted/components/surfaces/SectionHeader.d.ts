import * as React from 'react';
export interface SectionHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style' | 'title'> {
  title: React.ReactNode;
  /** Mono secondary value: counts, ids, timestamps. */
  meta?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  size?: 'md' | 'lg';
  style?: React.CSSProperties;
}
export declare function SectionHeader(props: SectionHeaderProps): JSX.Element;
