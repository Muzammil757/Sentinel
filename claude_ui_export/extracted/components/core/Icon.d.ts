import * as React from 'react';
export interface IconProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Lucide icon name, kebab-case (e.g. "shield-check", "git-branch"). */
  name: string;
  /** Rendered box in px. Use 14 inside dense rows, 16 default, 20 for headers. */
  size?: number;
  strokeAlign?: string;
}
export declare function Icon(props: IconProps): JSX.Element;
