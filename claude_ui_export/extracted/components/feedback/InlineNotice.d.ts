import * as React from 'react';
/**
 * In-context explanation of a constraint, block reason or authority boundary.
 * @startingPoint section="Feedback" subtitle="Notices, dialogs and transient toasts" viewport="700x300"
 */
export interface InlineNoticeProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style' | 'title'> {
  tone?: 'info' | 'attention' | 'blocked' | 'neutral';
  title?: React.ReactNode;
  actions?: React.ReactNode;
  /** Overrides the tone's default Lucide glyph. */
  icon?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}
export declare function InlineNotice(props: InlineNoticeProps): JSX.Element;
