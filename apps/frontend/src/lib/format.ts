import { formatDistanceToNowStrict } from "date-fns";

export function formatBytes(bytes: number): string {
  if (bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const level = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** level;
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[level]}`;
}

export function formatAgo(date: string): string {
  return formatDistanceToNowStrict(new Date(date), { addSuffix: true });
}

export function formatSeconds(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const sec = seconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${sec}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${sec}s`;
  }
  return `${sec}s`;
}
