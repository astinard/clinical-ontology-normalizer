"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getDocument, Document } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-500",
  processing: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

export default function DocumentsPage() {
  const [documentId, setDocumentId] = useState("");
  const [document, setDocument] = useState<Document | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!documentId.trim()) {
      toast.error("Please enter a document ID");
      return;
    }

    setIsLoading(true);
    try {
      const doc = await getDocument(documentId.trim());
      setDocument(doc);
    } catch (error) {
      console.error("Failed to fetch document:", error);
      toast.error("Document not found or backend unavailable");
      setDocument(null);
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
              Documents
            </h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="mx-auto max-w-2xl space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Find Document</CardTitle>
              <CardDescription>
                Enter a document ID to view its details
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSearch} className="flex gap-4">
                <Input
                  placeholder="Document ID (UUID)"
                  value={documentId}
                  onChange={(e) => setDocumentId(e.target.value)}
                />
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Searching..." : "Search"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {document && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{document.note_type}</CardTitle>
                    <CardDescription>
                      Patient: {document.patient_id}
                    </CardDescription>
                  </div>
                  <Badge className={STATUS_COLORS[document.status] || "bg-gray-500"}>
                    {document.status.toUpperCase()}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg bg-zinc-100 p-4 dark:bg-zinc-800">
                  <p className="line-clamp-3 font-mono text-sm">
                    {document.text}
                  </p>
                </div>
                <div className="flex gap-4">
                  <Link href={`/documents/${document.id}`}>
                    <Button>View Full Document</Button>
                  </Link>
                  <Link href={`/patients/${document.patient_id}/graph`}>
                    <Button variant="outline">View Patient Graph</Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Upload New Document</CardTitle>
              <CardDescription>
                Upload a clinical note for processing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/documents/upload">
                <Button variant="outline" className="w-full">
                  Upload Document
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
