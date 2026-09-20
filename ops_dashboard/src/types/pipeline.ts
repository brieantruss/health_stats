/**
 * TypeScript definitions for Health Stats Pipeline Telemetry & Pub/Sub event bus.
 */

export type HealthDataType =
  | 'blood_pressure'
  | 'cycling'
  | 'heart_rate'
  | 'locations'
  | 'oxygen'
  | 'running'
  | 'shootaround'
  | 'sleep'
  | 'steps'
  | 'swimming'
  | 'vo2max'
  | 'walking'
  | 'weather';

export interface CategoryTelemetry {
  category: HealthDataType;
  totalFiles: number;
  pendingRawFiles: number;
  totalSizeBytes: number;
  totalSizeFormatted: string;
  latestFileName: string | null;
  latestFileModifiedAt: string | null; // ISO 8601 string
  latestFileSizeBytes: number | null;
  latestFileSizeFormatted: string | null;
  status: 'active' | 'idle' | 'processing' | 'error';
  lastEventAt?: string;
  isPulsing?: boolean;
}

export interface LatestIngestionSummary {
  category: HealthDataType | null;
  fileName: string | null;
  timestamp: string | null;
}

export interface PipelineStatusResponse {
  serverTime: string;
  totalCategories: number;
  grandTotalFiles: number;
  grandTotalSizeBytes: number;
  grandTotalSizeFormatted: string;
  latestIngestion: LatestIngestionSummary;
  categories: Record<HealthDataType, CategoryTelemetry>;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

/**
 * Pub/Sub Event Stream Models (Discriminated Union)
 */
export interface BaseEvent {
  id?: number;
  timestamp: string;
}

export interface InitialStateEvent extends BaseEvent {
  eventType: 'INITIAL_STATE';
  payload: PipelineStatusResponse;
}

export interface TelemetryUpdateEvent extends BaseEvent {
  eventType: 'TELEMETRY_UPDATE';
  payload: PipelineStatusResponse;
}

export interface FileDetectedEvent extends BaseEvent {
  eventType: 'FILE_DETECTED';
  payload: {
    category: HealthDataType;
    fileName: string;
    fileSizeBytes?: number;
    source?: string;
  };
}

export interface FileProcessedEvent extends BaseEvent {
  eventType: 'FILE_PROCESSED';
  payload: {
    category: HealthDataType;
    fileName: string;
    rowCount?: number;
    destination?: 'mysql' | 'bigquery';
    durationMs?: number;
  };
}

export interface WorkoutLoggedEvent extends BaseEvent {
  eventType: 'workout_logged';
  payload: {
    exercise: string;
    reps?: number;
    weight?: number;
    notes?: string;
  };
}

export interface SleepSummaryReadyEvent extends BaseEvent {
  eventType: 'sleep_summary_ready';
  payload: {
    total_hours: number;
    deep_sleep_hours?: number;
    rem_sleep_hours?: number;
    quality_score?: number;
  };
}

export interface PipelineErrorEvent extends BaseEvent {
  eventType: 'PIPELINE_ERROR';
  payload: {
    category?: HealthDataType;
    fileName?: string;
    stage: 'ingest' | 'transform' | 'load_bigquery' | 'validation';
    message: string;
  };
}

export interface GenericPubSubEvent extends BaseEvent {
  eventType: string;
  payload: Record<string, unknown>;
  status?: string;
  processedAt?: string | null;
}

export type PipelineEvent =
  | InitialStateEvent
  | TelemetryUpdateEvent
  | FileDetectedEvent
  | FileProcessedEvent
  | WorkoutLoggedEvent
  | SleepSummaryReadyEvent
  | PipelineErrorEvent
  | GenericPubSubEvent;

export interface CategoryMetadata {
  label: string;
  iconName: string;
  color: string;
  accentBg: string;
  borderColor: string;
  description: string;
}
