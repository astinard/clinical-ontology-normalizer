"use client";

import { useEffect, useState, useCallback } from "react";
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
import {
  getDocument,
  getDocumentMentions,
  previewExtraction,
  Document,
  Mention,
  ExtractedMentionPreview,
} from "@/lib/api";
import {
  MentionHighlighter,
  MentionLegend,
  MentionDetail,
} from "@/components/MentionHighlighter";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-500",
  processing: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

interface MentionSpan {
  text: string;
  start_offset: number;
  end_offset: number;
  assertion: string;
  temporality: string;
  confidence: number;
  section: string | null;
  domain?: string | null;
}

export default function DocumentViewerPage() {
  const params = useParams();
  const documentId = params.documentId as string;
  const [document, setDocument] = useState<Document | null>(null);
  const [mentions, setMentions] = useState<MentionSpan[]>([]);
  const [selectedMention, setSelectedMention] = useState<MentionSpan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingMentions, setIsLoadingMentions] = useState(false);
  const [extractionTime, setExtractionTime] = useState<number | null>(null);

  useEffect(() => {
    if (!documentId) return;

    const fetchDocument = async () => {
      try {
        const doc = await getDocument(documentId);
        setDocument(doc);
        setError(null);

        // If document is completed, fetch stored mentions
        if (doc.status === "completed") {
          try {
            const dbMentions = await getDocumentMentions(documentId);
            const mentionSpans: MentionSpan[] = dbMentions.map((m) => ({
              text: m.text,
              start_offset: m.start_offset,
              end_offset: m.end_offset,
              assertion: m.assertion,
              temporality: m.temporality,
              confidence: m.confidence,
              section: m.section,
              domain: null, // DB mentions don't have domain stored in Mention table
            }));
            setMentions(mentionSpans);
          } catch {
            // No mentions yet, that's ok
          }
        }
      } catch (err) {
        console.error("Failed to fetch document:", err);
        setError("Failed to fetch document. Is the backend running?");
      }
    };

    fetchDocument();
  }, [documentId]);

  const handlePreviewExtraction = useCallback(async () => {
    if (!document) return;

    setIsLoadingMentions(true);
    setSelectedMention(null);
    try {
      const result = await previewExtraction(document.text, document.note_type);
      const mentionSpans: MentionSpan[] = result.mentions.map((m) => ({
        text: m.text,
        start_offset: m.start_offset,
        end_offset: m.end_offset,
        assertion: m.assertion,
        temporality: m.temporality,
        confidence: m.confidence,
        section: m.section,
        domain: m.domain,
      }));
      setMentions(mentionSpans);
      setExtractionTime(result.extraction_time_ms);
    } catch (err) {
      console.error("Failed to preview extraction:", err);
    } finally {
      setIsLoadingMentions(false);
    }
  }, [document]);

  const handleMentionClick = useCallback((mention: MentionSpan) => {
    setSelectedMention(mention);
  }, []);

  // Group mentions by domain for summary
  const mentionsByDomain = mentions.reduce(
    (acc, m) => {
      const domain = m.domain || "Unknown";
      acc[domain] = (acc[domain] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

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
          <div className="mx-auto max-w-5xl space-y-6">
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
                <TabsTrigger value="mentions">
                  Mentions {mentions.length > 0 && `(${mentions.length})`}
                </TabsTrigger>
                <TabsTrigger value="metadata">Metadata</TabsTrigger>
              </TabsList>

              <TabsContent value="document">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>Clinical Note</CardTitle>
                        <CardDescription>
                          {mentions.length > 0
                            ? `${mentions.length} mentions highlighted`
                            : "Click 'Extract Mentions' to highlight clinical terms"}
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        {extractionTime !== null && (
                          <span className="text-sm text-zinc-500">
                            {extractionTime.toFixed(1)}ms
                          </span>
                        )}
                        <Button
                          onClick={handlePreviewExtraction}
                          disabled={isLoadingMentions}
                          size="sm"
                        >
                          {isLoadingMentions ? (
                            <>
                              <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
                              Extracting...
                            </>
                          ) : (
                            "Extract Mentions"
                          )}
                        </Button>
                      </div>
                    </div>
                    {mentions.length > 0 && <MentionLegend className="mt-4" />}
                  </CardHeader>
                  <CardContent>
                    <MentionHighlighter
                      text={document.text}
                      mentions={mentions}
                      onMentionClick={handleMentionClick}
                      selectedMention={selectedMention}
                    />
                  </CardContent>
                </Card>

                {selectedMention && (
                  <Card className="mt-4">
                    <CardHeader>
                      <CardTitle className="text-lg">Mention Details</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <MentionDetail mention={selectedMention} />
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="mentions">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>Extracted Mentions</CardTitle>
                        <CardDescription>
                          {mentions.length > 0
                            ? `${mentions.length} clinical terms extracted`
                            : "No mentions extracted yet"}
                        </CardDescription>
                      </div>
                      {mentions.length === 0 && (
                        <Button onClick={handlePreviewExtraction} disabled={isLoadingMentions}>
                          Extract Now
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {mentions.length > 0 ? (
                      <div className="space-y-6">
                        {/* Summary by domain */}
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(mentionsByDomain)
                            .sort(([, a], [, b]) => b - a)
                            .map(([domain, count]) => (
                              <Badge key={domain} variant="outline">
                                {domain}: {count}
                              </Badge>
                            ))}
                        </div>

                        {/* Mention table */}
                        <div className="rounded-lg border">
                          <table className="w-full text-sm">
                            <thead className="border-b bg-zinc-50 dark:bg-zinc-800">
                              <tr>
                                <th className="px-4 py-2 text-left font-medium">Text</th>
                                <th className="px-4 py-2 text-left font-medium">Domain</th>
                                <th className="px-4 py-2 text-left font-medium">Assertion</th>
                                <th className="px-4 py-2 text-left font-medium">Section</th>
                                <th className="px-4 py-2 text-right font-medium">Confidence</th>
                              </tr>
                            </thead>
                            <tbody>
                              {mentions.map((m, i) => (
                                <tr
                                  key={i}
                                  className="border-b last:border-0 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 cursor-pointer"
                                  onClick={() => setSelectedMention(m)}
                                >
                                  <td className="px-4 py-2 font-medium">{m.text}</td>
                                  <td className="px-4 py-2">
                                    <Badge variant="outline" className="text-xs">
                                      {m.domain || "Unknown"}
                                    </Badge>
                                  </td>
                                  <td className="px-4 py-2 capitalize">{m.assertion}</td>
                                  <td className="px-4 py-2 text-zinc-500">
                                    {m.section || "-"}
                                  </td>
                                  <td className="px-4 py-2 text-right">
                                    {(m.confidence * 100).toFixed(0)}%
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-zinc-500">
                        <p>Click &quot;Extract Now&quot; to run NLP extraction.</p>
                        <p className="text-sm mt-2">
                          This will identify clinical terms in the document.
                        </p>
                      </div>
                    )}
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
