import * as React from 'react';
export interface TagProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'style'> {
  icon?: string;
  /** Renders a dismiss affordance when provided. */
  onRemove?: () => void;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}
export declare function Tag(props: TagProps): JSX.Element;
