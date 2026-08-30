import * as React from 'react';
export interface SelectOption { value: string; label: string }
export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size' | 'style'> {
  label?: string;
  options?: Array<string | SelectOption>;
  hint?: string;
  size?: 'md' | 'lg';
  style?: React.CSSProperties;
  wrapperStyle?: React.CSSProperties;
}
export declare function Select(props: SelectProps): JSX.Element;
