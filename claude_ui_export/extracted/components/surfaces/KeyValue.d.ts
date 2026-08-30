import * as React from 'react';
export interface KeyValueItem { label: React.ReactNode; value: React.ReactNode; mono?: boolean }
export interface KeyValueProps extends Omit<React.HTMLAttributes<HTMLDListElement>, 'style'> {
  items: KeyValueItem[];
  columns?: number;
  dense?: boolean;
  style?: React.CSSProperties;
}
export declare function KeyValue(props: KeyValueProps): JSX.Element;
