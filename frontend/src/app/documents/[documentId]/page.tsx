"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getDocument, Document } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-500",
  processing: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

export default function DocumentViewerPage() {
  const params = useParams();
  const documentId = params.documentId as string;
  const [document, setDocument] = useState<Document | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) return;

    const fetchDocument = async () => {
      try {
        const doc = await getDocument(documentId);
        setDocument(doc);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch document:", err);
        setError("Failed to fetch document. Is the backend running?");
      }
    };

    fetchDocument();
  }, [documentId]);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <header className="border-b bg-white dark:bg-zinc-950">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
              &larr; Home
            </Link>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              Document Viewer
            </h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {error ? (
          <Card className="mx-auto max-w-4xl">
            <CardContent className="py-8">
              <div className="rounded-lg bg-red-50 p-4 text-red-800 dark:bg-red-900/20 dark:text-red-200">
                {error}
              </div>
            </CardContent>
          </Card>
        ) : document ? (
          <div className="mx-auto max-w-4xl space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{document.note_type}</CardTitle>
                    <CardDescription>
                      Patient: {document.patient_id} | Document ID: {document.id}
                    </CardDescription>
                  </div>
                  <Badge className={STATUS_COLORS[document.status] || "bg-gray-500"}>
                    {document.status.toUpperCase()}
                  </Badge>
                </div>
              </CardHeader>
            </Card>

            <Tabs defaultValue="document" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="document">Document</TabsTrigger>
                <TabsTrigger value="mentions">Mentions</TabsTrigger>
                <TabsTrigger value="metadata">Metadata</TabsTrigger>
              </TabsList>

              <TabsContent value="document">
                <Card>
                  <CardHeader>
                    <CardTitle>Clinical Note</CardTitle>
                    <CardDescription>
                      Original document text with highlighted mentions (when available)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="whitespace-pre-wrap rounded-lg bg-zinc-100 p-4 font-mono text-sm dark:bg-zinc-800">
                      {document.text}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="mentions">
                <Card>
                  <CardHeader>
                    <CardTitle>Extracted Mentions</CardTitle>
                    <CardDescription>
                      Clinical mentions extracted from the document text
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-8 text-zinc-500">
                      <p>Mention extraction data will be displayed here.</p>
                      <p className="text-sm mt-2">
                        This feature requires additional API endpoints.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="metadata">
                <Card>
                  <CardHeader>
                    <CardTitle>Document Metadata</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl className="grid grid-cols-2 gap-4">
                      <div>
                        <dt className="text-sm font-medium text-zinc-500">Patient ID</dt>
                        <dd className="text-lg">{document.patient_id}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-zinc-500">Note Type</dt>
                        <dd className="text-lg">{document.note_type}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-zinc-500">Status</dt>
                        <dd className="text-lg">{document.status}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-zinc-500">Created</dt>
                        <dd className="text-lg">
                          {new Date(document.created_at).toLocaleString()}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-zinc-500">Processed</dt>
                        <dd className="text-lg">
                          {document.processed_at
                            ? new Date(document.processed_at).toLocaleString()
                            : "Not yet"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-zinc-500">Job ID</dt>
                        <dd className="text-lg font-mono text-xs">{document.job_id}</dd>
                      </div>
                    </dl>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            <div className="flex gap-4">
              <Link href={`/patients/${document.patient_id}/graph`}>
                <Button>View Patient Graph</Button>
              </Link>
              <Link href={`/jobs/${document.job_id}`}>
                <Button variant="outline">View Job Status</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-zinc-900" />
          </div>
        )}
      </main>
    </div>
  );
}
