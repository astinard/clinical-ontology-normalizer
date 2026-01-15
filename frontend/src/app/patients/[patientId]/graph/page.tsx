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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getPatientGraph, buildPatientGraph, PatientGraph, GraphNode } from "@/lib/api";
import { toast } from "sonner";

const NODE_TYPE_COLORS: Record<string, string> = {
  patient: "bg-purple-100 text-purple-800",
  condition: "bg-red-100 text-red-800",
  drug: "bg-blue-100 text-blue-800",
  measurement: "bg-green-100 text-green-800",
  procedure: "bg-orange-100 text-orange-800",
  observation: "bg-gray-100 text-gray-800",
};

const EDGE_TYPE_LABELS: Record<string, string> = {
  has_condition: "Has Condition",
  takes_drug: "Takes Drug",
  has_measurement: "Has Measurement",
  has_procedure: "Has Procedure",
  has_observation: "Has Observation",
  condition_treated_by: "Treated By",
  drug_treats: "Treats",
};

export default function PatientGraphPage() {
  const params = useParams();
  const patientId = params.patientId as string;
  const [graph, setGraph] = useState<PatientGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);

  const fetchGraph = useCallback(async () => {
    try {
      const patientGraph = await getPatientGraph(patientId);
      setGraph(patientGraph);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch graph:", err);
      setError("No graph data found for this patient. Try building the graph.");
    }
  }, [patientId]);

  useEffect(() => {
    if (!patientId) return;
    fetchGraph();
  }, [patientId, fetchGraph]);

  const handleBuildGraph = async () => {
    setIsBuilding(true);
    try {
      const newGraph = await buildPatientGraph(patientId);
      setGraph(newGraph);
      setError(null);
      toast.success("Graph built successfully");
    } catch (err) {
      console.error("Failed to build graph:", err);
      toast.error("Failed to build graph. Make sure patient has clinical facts.");
    } finally {
      setIsBuilding(false);
    }
  };

  // Group nodes by type for the visualization
  const nodesByType = graph?.nodes.reduce(
    (acc, node) => {
      const type = node.node_type;
      if (!acc[type]) acc[type] = [];
      acc[type].push(node);
      return acc;
    },
    {} as Record<string, GraphNode[]>
  ) || {};

  // Find node label by ID
  const getNodeLabel = (nodeId: string) => {
    const node = graph?.nodes.find((n) => n.id === nodeId);
    return node?.label || nodeId;
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <header className="border-b bg-white dark:bg-zinc-950">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/patients" className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
                &larr; Patients
              </Link>
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                Patient {patientId} - Knowledge Graph
              </h1>
            </div>
            <Button onClick={handleBuildGraph} disabled={isBuilding} variant="outline">
              {isBuilding ? "Building..." : "Rebuild Graph"}
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {error && !graph ? (
          <Card className="mx-auto max-w-2xl">
            <CardContent className="py-8 text-center">
              <p className="text-zinc-500 mb-4">{error}</p>
              <Button onClick={handleBuildGraph} disabled={isBuilding}>
                {isBuilding ? "Building Graph..." : "Build Graph"}
              </Button>
            </CardContent>
          </Card>
        ) : graph ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Total Nodes</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{graph.node_count}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Total Edges</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{graph.edge_count}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Conditions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{nodesByType.condition?.length || 0}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-zinc-500">Drugs</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{nodesByType.drug?.length || 0}</div>
                </CardContent>
              </Card>
            </div>

            {/* Tabs for different views */}
            <Tabs defaultValue="nodes" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="nodes">Nodes</TabsTrigger>
                <TabsTrigger value="edges">Edges</TabsTrigger>
                <TabsTrigger value="visual">Visual</TabsTrigger>
              </TabsList>

              <TabsContent value="nodes">
                <Card>
                  <CardHeader>
                    <CardTitle>Graph Nodes</CardTitle>
                    <CardDescription>
                      All clinical entities for this patient
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Type</TableHead>
                          <TableHead>Label</TableHead>
                          <TableHead>OMOP ID</TableHead>
                          <TableHead>Properties</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {graph.nodes.map((node) => (
                          <TableRow key={node.id}>
                            <TableCell>
                              <Badge className={NODE_TYPE_COLORS[node.node_type] || "bg-gray-100"}>
                                {node.node_type}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-medium">{node.label}</TableCell>
                            <TableCell>{node.omop_concept_id || "-"}</TableCell>
                            <TableCell>
                              {Object.entries(node.properties || {}).map(([key, value]) => (
                                <span key={key} className="mr-2 text-xs text-zinc-500">
                                  {key}: {String(value)}
                                </span>
                              ))}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="edges">
                <Card>
                  <CardHeader>
                    <CardTitle>Graph Edges</CardTitle>
                    <CardDescription>
                      Relationships between entities
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Source</TableHead>
                          <TableHead>Relationship</TableHead>
                          <TableHead>Target</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {graph.edges.map((edge) => (
                          <TableRow key={edge.id}>
                            <TableCell>{getNodeLabel(edge.source_node_id)}</TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {EDGE_TYPE_LABELS[edge.edge_type] || edge.edge_type}
                              </Badge>
                            </TableCell>
                            <TableCell>{getNodeLabel(edge.target_node_id)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="visual">
                <Card>
                  <CardHeader>
                    <CardTitle>Graph Visualization</CardTitle>
                    <CardDescription>
                      Simple visual representation of the patient knowledge graph
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-col items-center space-y-8 py-8">
                      {/* Patient node at center */}
                      <div className="rounded-full bg-purple-200 px-6 py-3 text-purple-800 font-semibold">
                        Patient {patientId}
                      </div>

                      {/* Connections */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full">
                        {Object.entries(nodesByType)
                          .filter(([type]) => type !== "patient")
                          .map(([type, nodes]) => (
                            <div key={type} className="space-y-2">
                              <h4 className="text-center font-semibold capitalize">{type}s</h4>
                              <div className="space-y-1">
                                {nodes.slice(0, 5).map((node) => (
                                  <div
                                    key={node.id}
                                    className={`rounded px-3 py-1 text-sm ${NODE_TYPE_COLORS[type] || "bg-gray-100"}`}
                                  >
                                    {node.label}
                                    {Boolean(node.properties?.is_negated) && (
                                      <span className="ml-2 text-red-600">(negated)</span>
                                    )}
                                  </div>
                                ))}
                                {nodes.length > 5 && (
                                  <div className="text-center text-xs text-zinc-500">
                                    +{nodes.length - 5} more
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
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
