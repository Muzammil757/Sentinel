import * as React from 'react';
export interface SideNavItem { value: string; label: React.ReactNode; icon: string; count?: number; attention?: boolean }
export interface SideNavSection { label?: React.ReactNode; items: SideNavItem[] }
export interface SideNavProps extends Omit<React.HTMLAttributes<HTMLElement>, 'style'> {
  sections: SideNavSection[];
  value?: string;
  onSelect?: (value: string) => void;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function SideNav(props: SideNavProps): JSX.Element;
