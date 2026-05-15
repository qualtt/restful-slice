import axios from "axios";
import type { Order, Paginated, PrintProfile, UploadedFile } from "../types/api";

export interface TelemetryEvent {
  id: string;
  name: string;
  ts: string;
  sessionId: string;
  route: string;
  consentVersion: string;
  context: {
    appVersion: string;
    environment: string;
    timezone: string;
    language: string;
  };
  data: Record<string, unknown>;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  timeout: 12_000
});

export async function getOrders(): Promise<Paginated<Order>> {
  const response = await api.get<Paginated<Order>>("/api/orders");
  return response.data;
}

export async function uploadFile(file: File): Promise<UploadedFile> {
  const payload = new FormData();
  payload.append("file", file);
  const response = await api.post<UploadedFile>("/api/orders/files", payload);
  return response.data;
}

export async function createOrder(params: {
  fileId: string;
  profileId: number;
}): Promise<Order> {
  const response = await api.post<Order>("/api/orders", params);
  return response.data;
}

export async function getProfiles(): Promise<Paginated<PrintProfile>> {
  const response = await api.get<Paginated<PrintProfile>>("/api/inventory/profiles");
  return response.data;
}

export async function syncTelemetryBatch(events: TelemetryEvent[]): Promise<void> {
  if (!events.length) {
    return;
  }

  const endpoint = import.meta.env.VITE_ANALYTICS_ENDPOINT ?? "/api/telemetry/events";
  await api.post(endpoint, {
    source: "restful-slice-frontend",
    events
  });
}
