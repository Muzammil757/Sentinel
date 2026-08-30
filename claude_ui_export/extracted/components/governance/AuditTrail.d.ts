import * as React from 'react';
export interface AuditEntry {
  time: React.ReactNode;
  actor: React.ReactNode;
  actorKind?: 'system' | 'govern' | 'agent' | 'execution' | 'reviewer';
  message: React.ReactNode;
  detail?: React.ReactNode;
}
export interface AuditTrailProps extends Omit<React.HTMLAttributes<HTMLOListElement>, 'style'> {
  entries: AuditEntry[];
  style?: React.CSSProperties;
}
export declare function AuditTrail(props: AuditTrailProps): JSX.Element;
