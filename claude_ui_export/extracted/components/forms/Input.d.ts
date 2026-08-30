import * as React from 'react';
/**
 * Single-line text field.
 * @startingPoint section="Forms" subtitle="Fields, selects, toggles and choice controls" viewport="700x260"
 */
export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size' | 'style'> {
  label?: string;
  hint?: string;
  /** Sets the error state and replaces the hint. */
  error?: string;
  icon?: string;
  /** Mono type for ids, hashes and thresholds. */
  mono?: boolean;
  size?: 'md' | 'lg';
  style?: React.CSSProperties;
  wrapperStyle?: React.CSSProperties;
}
export declare function Input(props: InputProps): JSX.Element;
