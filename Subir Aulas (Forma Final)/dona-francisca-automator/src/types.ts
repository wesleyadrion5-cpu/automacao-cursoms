export type LogLevel = 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
}

export interface MappedRow {
  id: string;
  modulo: string;
  video: string;
  duracao: string;
  extra: string;
}

export interface AutomationConfig {
  robotName: string;
  delayBetweenSteps: number; // in milliseconds
  autoScrollLogs: boolean;
  targetPlatform: string;
}

export type AutomationState = 'IDLE' | 'PREPARED' | 'MIGRATING' | 'COMPLETED' | 'PAUSED';
