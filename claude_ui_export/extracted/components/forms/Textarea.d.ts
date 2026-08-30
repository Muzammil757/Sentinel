import * as React from 'react';
export interface TextareaProps extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'style'> {
  label?: string;
  hint?: string;
  /** Right-aligned character/word counter string, e.g. "128/500". */
  counter?: string;
  style?: React.CSSProperties;
  wrapperStyle?: React.CSSProperties;
}
export declare function Textarea(props: TextareaProps): JSX.Element;
