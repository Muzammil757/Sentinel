import * as React from 'react';
export interface TabItem { value: string; label: React.ReactNode; count?: number }
/**
 * Underline tab bar for switching views within one screen.
 * @startingPoint section="Navigation" subtitle="Tab bar and application sidebar" viewport="700x320"
 */
export interface TabsProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
  items: Array<string | TabItem>;
  value?: string;
  onChange?: (value: string) => void;
  style?: React.CSSProperties;
}
export declare function Tabs(props: TabsProps): JSX.Element;
