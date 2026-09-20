import { HealthDataType, CategoryMetadata } from '../types/pipeline';

export const CATEGORY_CONFIG: Record<HealthDataType, CategoryMetadata> = {
  heart_rate: {
    label: 'Heart Rate',
    iconName: 'HeartPulse',
    color: 'text-rose-400',
    accentBg: 'bg-rose-500/10',
    borderColor: 'border-rose-500/30',
    description: 'Continuous beats per minute & rest trends',
  },
  sleep: {
    label: 'Sleep & Stages',
    iconName: 'Moon',
    color: 'text-indigo-400',
    accentBg: 'bg-indigo-500/10',
    borderColor: 'border-indigo-500/30',
    description: 'Deep, REM, light sleep durations',
  },
  steps: {
    label: 'Step Counts',
    iconName: 'Footprints',
    color: 'text-emerald-400',
    accentBg: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/30',
    description: 'Daily step cadence & active walking periods',
  },
  walking: {
    label: 'Walking Sessions',
    iconName: 'Navigation',
    color: 'text-teal-400',
    accentBg: 'bg-teal-500/10',
    borderColor: 'border-teal-500/30',
    description: 'GPS tracks, outdoor pace & elevation',
  },
  running: {
    label: 'Running Runs',
    iconName: 'Flame',
    color: 'text-orange-400',
    accentBg: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    description: 'High-intensity runs, splits & heart zones',
  },
  cycling: {
    label: 'Cycling',
    iconName: 'Bike',
    color: 'text-cyan-400',
    accentBg: 'bg-cyan-500/10',
    borderColor: 'border-cyan-500/30',
    description: 'Ride distance, average velocity & power',
  },
  swimming: {
    label: 'Swimming',
    iconName: 'Waves',
    color: 'text-sky-400',
    accentBg: 'bg-sky-500/10',
    borderColor: 'border-sky-500/30',
    description: 'Lap metrics, stroke styles & efficiency',
  },
  shootaround: {
    label: 'Shootarounds',
    iconName: 'CircleDot',
    color: 'text-amber-400',
    accentBg: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    description: 'Basketball shooting & court movement',
  },
  blood_pressure: {
    label: 'Blood Pressure',
    iconName: 'Activity',
    color: 'text-red-400',
    accentBg: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    description: 'Systolic, diastolic & pulse logs',
  },
  oxygen: {
    label: 'Oxygen (SpO2)',
    iconName: 'Wind',
    color: 'text-blue-400',
    accentBg: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    description: 'Blood oxygen saturation percentages',
  },
  vo2max: {
    label: 'VO2 Max',
    iconName: 'Gauge',
    color: 'text-violet-400',
    accentBg: 'bg-violet-500/10',
    borderColor: 'border-violet-500/30',
    description: 'Cardiorespiratory fitness measurements',
  },
  locations: {
    label: 'Locations / GPS',
    iconName: 'MapPin',
    color: 'text-amber-300',
    accentBg: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    description: 'Raw GPS coordinates & geocoded points',
  },
  weather: {
    label: 'Weather & AQI',
    iconName: 'CloudSun',
    color: 'text-yellow-400',
    accentBg: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    description: 'Ambient temperature, humidity & air quality',
  },
};

/**
 * Format relative time (e.g., "5m ago", "2h ago", "Yesterday")
 */
export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return 'Never';
  
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return 'Invalid date';

  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 5) return 'Just now';
  if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
  
  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) return `${diffInMinutes}m ago`;

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return `${diffInHours}h ago`;

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays === 1) return 'Yesterday';
  if (diffInDays < 30) return `${diffInDays}d ago`;

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/**
 * Format exact ISO string into clean display format
 */
export function formatExactDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return '—';
  
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
}

/**
 * Format byte size into readable unit
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return '0 B';
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
