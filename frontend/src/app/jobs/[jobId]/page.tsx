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
import { Progress } from "@/components/ui/progress";
import { getJobStatus, JobInfo } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-500",
  processing: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

const STATUS_PROGRESS: Record<string, number> = {
  queued: 10,
  processing: 50,
  completed: 100,
  failed: 100,
};

export default function JobStatusPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const [job, setJob] = useState<JobInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    if (!jobId || !polling) return;

    const fetchStatus = async () => {
      try {
        const status = await getJobStatus(jobId);
        setJob(status);
        setError(null);

        // Stop polling if job is completed or failed
        if (status.status === "completed" || status.status === "failed") {
          setPolling(false);
        }
      } catch (err) {
        console.error("Failed to fetch job status:", err);
        setError("Failed to fetch job status. Is the backend running?");
        setPolling(false);
      }
    };

    fetchStatus();

    // Poll every 2 seconds while processing
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [jobId, polling]);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <header className="border-b bg-white dark:bg-zinc-950">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
              &larr; Home
            </Link>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              Job Status
            </h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Processing Job</span>
              {job && (
                <Badge className={STATUS_COLORS[job.status] || "bg-gray-500"}>
                  {job.status.toUpperCase()}
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Job ID: <code className="text-xs">{jobId}</code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {error ? (
              <div className="rounded-lg bg-red-50 p-4 text-red-800 dark:bg-red-900/20 dark:text-red-200">
                {error}
              </div>
            ) : job ? (
              <>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Progress</span>
                    <span>{STATUS_PROGRESS[job.status] || 0}%</span>
                  </div>
                  <Progress value={STATUS_PROGRESS[job.status] || 0} />
                </div>

                {job.status === "completed" && job.result && (
                  <div className="space-y-4">
                    <div className="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
                      <h3 className="font-semibold text-green-800 dark:text-green-200">
                        Processing Complete
                      </h3>
                      <p className="mt-2 text-sm text-green-700 dark:text-green-300">
                        Extracted {(job.result as Record<string, number>).mention_count || 0} mentions
                        with {(job.result as Record<string, number>).candidate_count || 0} concept candidates.
                      </p>
                    </div>

                    <div className="flex gap-4">
                      <Link href={`/documents/${(job.result as Record<string, string>).document_id}`}>
                        <Button>View Document</Button>
                      </Link>
                      <Link href={`/patients/${(job.result as Record<string, string>).patient_id}/graph`}>
                        <Button variant="outline">View Patient Graph</Button>
                      </Link>
                    </div>
                  </div>
                )}

                {job.status === "failed" && (
                  <div className="rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
                    <h3 className="font-semibold text-red-800 dark:text-red-200">
                      Processing Failed
                    </h3>
                    <p className="mt-2 text-sm text-red-700 dark:text-red-300">
                      {job.error || "Unknown error occurred"}
                    </p>
                  </div>
                )}

                {(job.status === "queued" || job.status === "processing") && (
                  <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
                    <h3 className="font-semibold text-blue-800 dark:text-blue-200">
                      {job.status === "queued" ? "Waiting in Queue" : "Processing..."}
                    </h3>
                    <p className="mt-2 text-sm text-blue-700 dark:text-blue-300">
                      {job.status === "queued"
                        ? "Your document is queued for processing. This page will update automatically."
                        : "NLP extraction in progress. This page will update automatically."}
                    </p>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-zinc-900" />
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
