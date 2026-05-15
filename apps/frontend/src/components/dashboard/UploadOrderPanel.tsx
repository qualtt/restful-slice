import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { createOrder, getProfiles, uploadFile } from "../../lib/api";
import { telemetry } from "../../lib/telemetry";
import { Card } from "../common/Card";
import type { PrintProfile } from "../../types/api";

export function UploadOrderPanel() {
  const queryClient = useQueryClient();
  const [profileId, setProfileId] = useState<number>(3);

  const profilesQuery = useQuery({
    queryKey: ["profiles"],
    queryFn: getProfiles
  });

  useEffect(() => {
    if (profilesQuery.isSuccess) {
      telemetry.track("inventory.profiles_loaded", {
        total: profilesQuery.data.meta.total
      });
    }
  }, [profilesQuery.isSuccess, profilesQuery.data]);

  useEffect(() => {
    if (profilesQuery.isError) {
      telemetry.track("inventory.profiles_failed");
    }
  }, [profilesQuery.isError]);

  const createMutation = useMutation({
    mutationFn: async (payload: { file: File; profileId: number }) => {
      telemetry.track("upload.funnel.started", {
        fileName: payload.file.name,
        size: payload.file.size,
        profileId: payload.profileId
      });

      const uploaded = await uploadFile(payload.file);
      telemetry.track("upload.file.success", {
        fileId: uploaded.fileId,
        fileName: uploaded.filename
      });

      const order = await createOrder({
        fileId: uploaded.fileId,
        profileId: payload.profileId
      });
      telemetry.track("upload.order.created", {
        orderId: order.orderId,
        profileId: order.profileId
      });
      return order;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (error) => {
      telemetry.trackError(error, { feature: "upload_order_panel" });
    }
  });

  const dropzone = useDropzone({
    accept: {
      "model/stl": [".stl"],
      "model/3mf": [".3mf"],
      "model/step": [".step", ".stp"],
      "application/octet-stream": [".stl", ".3mf", ".step", ".stp"]
    },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024,
    onDropAccepted: (files) => {
      const file = files[0];
      telemetry.track("upload.file.accepted", { fileName: file.name, fileSize: file.size });
      void createMutation.mutateAsync({ file, profileId });
    },
    onDropRejected: (rejections) => {
      telemetry.track("upload.file.rejected", {
        reason: rejections[0]?.errors?.[0]?.code ?? "unknown"
      });
    },
    onFileDialogOpen: () => telemetry.track("upload.dialog_opened")
  });

  const profiles: PrintProfile[] = profilesQuery.data?.data ?? [];

  return (
    <Card title="Upload and create order" className="space-y-4">
      <div>
        <p className="text-sm text-black">
          Drop STL/3MF/STEP file, choose print profile, and send to slicing queue.
        </p>
      </div>

      <label className="block text-sm text-black font-bold">
        Print profile:
        <select
          className="field mt-1"
          value={profileId}
          onChange={(event) => {
            const next = Number(event.target.value);
            setProfileId(next);
            telemetry.track("ux.profile.selected", { profileId: next });
          }}
        >
          {profiles.map((profile) => (
            <option key={profile.profileId} value={profile.profileId}>
              {profile.displayName} ({profile.material.materialType})
            </option>
          ))}
        </select>
      </label>

      <div
        {...dropzone.getRootProps()}
        className="cursor-pointer border-4 border-dashed border-[#39ff14] bg-[#1a1a1a] p-8 text-center transition hover:bg-[#2a2a2a] shadow-[0_0_15px_rgba(57,255,20,0.5)]"
      >
        <input {...dropzone.getInputProps()} />
        <p className="text-lg font-bold text-[#39ff14]">DRAG & DROP MODEL FILE HERE</p>
        <p className="mt-2 text-xs text-[#39ff14]/70">OR CLICK TO CHOOSE FROM DISK (MAX 100 MB)</p>
      </div>

      {createMutation.isPending && (
        <p className="text-sm text-blue-700 font-bold">Creating order and sending slicing request...</p>
      )}
      {createMutation.isSuccess && (
        <p className="text-sm text-green-700 font-bold">
          Order created: {createMutation.data.orderId.slice(0, 8)}...
        </p>
      )}
      {createMutation.isError && (
        <p className="text-sm text-red-700 font-bold">
          Failed to create order. See telemetry for error diagnostics.
        </p>
      )}
    </Card>
  );
}
