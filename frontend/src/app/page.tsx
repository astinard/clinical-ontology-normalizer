"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <header className="border-b bg-white dark:bg-zinc-950">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            Clinical Ontology Normalizer
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Ingest clinical notes, extract mentions, and map to OMOP concepts
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Upload Document</CardTitle>
              <CardDescription>
                Upload a clinical note for NLP processing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/documents/upload">
                <Button className="w-full">Upload Document</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>View Documents</CardTitle>
              <CardDescription>
                View uploaded documents and processing status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/documents">
                <Button variant="outline" className="w-full">
                  View Documents
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Patient Graphs</CardTitle>
              <CardDescription>
                View patient knowledge graphs with OMOP concepts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/patients">
                <Button variant="outline" className="w-full">
                  View Patients
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        <div className="mt-12">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Quick Start
          </h2>
          <ol className="list-decimal space-y-2 pl-6 text-zinc-600 dark:text-zinc-400">
            <li>Upload a clinical note (discharge summary, progress note, etc.)</li>
            <li>Wait for NLP processing to extract mentions</li>
            <li>View extracted mentions mapped to OMOP concepts</li>
            <li>Explore the patient knowledge graph</li>
          </ol>
        </div>
      </main>
    </div>
  );
}
