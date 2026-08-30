import * as React from 'react';
export interface PipelineStage {
  label: React.ReactNode;
  state: 'done' | 'active' | 'blocked' | 'halted' | 'skipped' | 'pending';
  /** Mono sub-line: duration, verdict, exit reason. */
  detail?: React.ReactNode;
}
/**
 * The governance pipeline made legible: INTAKE → WEIGH → GOVERN → EXECUTION → REVIEW.
 * @startingPoint section="Governance" subtitle="Pipeline, decisions, candidates and audit trail" viewport="700x360"
 */
export interface PipelineTrackProps extends Omit<React.HTMLAttributes<HTMLOListElement>, 'style'> {
  stages: PipelineStage[];
  orientation?: 'horizontal' | 'vertical';
  style?: React.CSSProperties;
}
export declare function PipelineTrack(props: PipelineTrackProps): JSX.Element;
