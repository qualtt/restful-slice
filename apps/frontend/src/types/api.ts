export type OrderStatus =
  | "pending"
  | "slicing"
  | "priced"
  | "confirmed"
  | "printing"
  | "completed"
  | "failed"
  | "cancelled";

export interface Money {
  amount: string;
  currency: string;
}

export interface SlicingResult {
  weightGrams: number;
  printTimeSeconds: number;
  price: Money;
}

export interface UploadedFile {
  fileId: string;
  filename: string;
  sizeBytes: number;
  uploadedAt: string;
}

export interface Order {
  orderId: string;
  status: OrderStatus;
  fileId: string;
  profileId: number;
  slicingResult?: SlicingResult;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Paginated<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    pageSize: number;
  };
}

export interface ProfileMaterial {
  materialId: number;
  label: string;
  materialType: string;
  remainingGrams: number;
}

export interface PrintProfile {
  profileId: number;
  displayName: string;
  material: ProfileMaterial;
  markupPercent: number;
  isEnabled: boolean;
  description?: string;
}
