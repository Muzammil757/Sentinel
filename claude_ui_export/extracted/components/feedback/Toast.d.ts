import * as React from 'react';
export interface ToastProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style' | 'title'> {
  tone?: 'neutral' | 'allowed' | 'blocked' | 'escalated';
  title: React.ReactNode;
  /** Mono secondary line: ids, timestamps, exit codes. */
  detail?: React.ReactNode;
  onDismiss?: () => void;
  style?: React.CSSProperties;
}
export declare function Toast(props: ToastProps): JSX.Element;
