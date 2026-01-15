"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { uploadDocument, DocumentCreate } from "@/lib/api";

const NOTE_TYPES = [
  "Discharge Summary",
  "Progress Note",
  "History & Physical",
  "Consultation Note",
  "Operative Report",
  "Radiology Report",
  "Pathology Report",
  "Emergency Department Note",
  "Other",
];

export default function UploadDocumentPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<DocumentCreate>({
    patient_id: "",
    note_type: NOTE_TYPES[0],
    text: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.patient_id.trim()) {
      toast.error("Patient ID is required");
      return;
    }

    if (!formData.text.trim()) {
      toast.error("Document text is required");
      return;
    }

    setIsLoading(true);

    try {
      const result = await uploadDocument(formData);
      toast.success("Document uploaded successfully");
      router.push(`/jobs/${result.job_id}`);
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error("Failed to upload document. Is the backend running?");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <header className="border-b bg-white dark:bg-zinc-950">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
              &larr; Home
            </Link>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              Upload Document
            </h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle>Upload Clinical Document</CardTitle>
            <CardDescription>
              Enter patient information and paste the clinical note text for NLP processing.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="patient_id">Patient ID</Label>
                <Input
                  id="patient_id"
                  placeholder="e.g., P001"
                  value={formData.patient_id}
                  onChange={(e) =>
                    setFormData({ ...formData, patient_id: e.target.value })
                  }
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="note_type">Note Type</Label>
                <select
                  id="note_type"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={formData.note_type}
                  onChange={(e) =>
                    setFormData({ ...formData, note_type: e.target.value })
                  }
                >
                  {NOTE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="text">Clinical Note Text</Label>
                <Textarea
                  id="text"
                  placeholder="Paste clinical note text here..."
                  className="min-h-[300px]"
                  value={formData.text}
                  onChange={(e) =>
                    setFormData({ ...formData, text: e.target.value })
                  }
                  required
                />
                <p className="text-sm text-zinc-500">
                  {formData.text.length} characters
                </p>
              </div>

              <div className="flex gap-4">
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Uploading..." : "Upload Document"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.back()}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
