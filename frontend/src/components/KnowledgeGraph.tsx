"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import type { GraphNode as APIGraphNode, GraphEdge as APIGraphEdge } from "@/lib/api";

// Extended types for D3 simulation
interface SimulationNode extends APIGraphNode {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  vx?: number;
  vy?: number;
}

interface SimulationEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  source: SimulationNode | string;
  target: SimulationNode | string;
}

interface KnowledgeGraphProps {
  nodes: APIGraphNode[];
  edges: APIGraphEdge[];
  patientId: string;
}

// Node type configuration with luminous colors
const NODE_CONFIG: Record<string, { color: string; glow: string; label: string }> = {
  patient: { color: "#a78bfa", glow: "#8b5cf6", label: "Patient" },
  condition: { color: "#f87171", glow: "#ef4444", label: "Conditions" },
  drug: { color: "#60a5fa", glow: "#3b82f6", label: "Drugs" },
  measurement: { color: "#4ade80", glow: "#22c55e", label: "Measurements" },
  procedure: { color: "#fb923c", glow: "#f97316", label: "Procedures" },
  observation: { color: "#94a3b8", glow: "#64748b", label: "Observations" },
  device: { color: "#f472b6", glow: "#ec4899", label: "Devices" },
};

const EDGE_LABELS: Record<string, string> = {
  has_condition: "has",
  takes_drug: "takes",
  has_measurement: "measured",
  has_procedure: "underwent",
  has_observation: "observed",
  has_device: "uses",
  condition_treated_by: "treated by",
  drug_treats: "treats",
};

export default function KnowledgeGraph({ nodes, edges, patientId }: KnowledgeGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimulationNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(Object.keys(NODE_CONFIG))
  );

  // Handle resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDimensions({ width, height: Math.max(height, 500) });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  // Toggle filter
  const toggleFilter = useCallback((nodeType: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(nodeType)) {
        next.delete(nodeType);
      } else {
        next.add(nodeType);
      }
      return next;
    });
  }, []);

  // D3 visualization
  useEffect(() => {
    if (!svgRef.current || !nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const { width, height } = dimensions;

    // Filter nodes and edges based on active filters
    const filteredNodes = nodes.filter((n) => activeFilters.has(n.node_type));
    const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = edges.filter(
      (e) =>
        filteredNodeIds.has(e.source_node_id) && filteredNodeIds.has(e.target_node_id)
    );

    // Create deep copies for D3 mutation
    const nodeData: SimulationNode[] = filteredNodes.map((n) => ({ ...n }));
    const edgeData: SimulationEdge[] = filteredEdges.map((e) => ({
      ...e,
      source: e.source_node_id,
      target: e.target_node_id,
    }));

    // Create node map for edge lookups
    const nodeMap = new Map(nodeData.map((n) => [n.id, n]));

    // Define gradients and filters for glow effects
    const defs = svg.append("defs");

    // Glow filter
    const filter = defs
      .append("filter")
      .attr("id", "glow")
      .attr("x", "-50%")
      .attr("y", "-50%")
      .attr("width", "200%")
      .attr("height", "200%");

    filter
      .append("feGaussianBlur")
      .attr("stdDeviation", "3")
      .attr("result", "coloredBlur");

    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // Stronger glow for selected
    const filterSelected = defs
      .append("filter")
      .attr("id", "glow-selected")
      .attr("x", "-100%")
      .attr("y", "-100%")
      .attr("width", "300%")
      .attr("height", "300%");

    filterSelected
      .append("feGaussianBlur")
      .attr("stdDeviation", "6")
      .attr("result", "coloredBlur");

    const feMergeSelected = filterSelected.append("feMerge");
    feMergeSelected.append("feMergeNode").attr("in", "coloredBlur");
    feMergeSelected.append("feMergeNode").attr("in", "SourceGraphic");

    // Arrow marker for edges
    defs
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "-0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .append("path")
      .attr("d", "M 0,-5 L 10 ,0 L 0,5")
      .attr("fill", "#475569")
      .style("stroke", "none");

    // Create zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on("zoom", (event) => {
        container.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Main container for zoom/pan
    const container = svg.append("g").attr("class", "graph-container");

    // Create force simulation
    const simulation = d3
      .forceSimulation<SimulationNode>(nodeData)
      .force(
        "link",
        d3
          .forceLink<SimulationNode, SimulationEdge>(edgeData)
          .id((d) => d.id)
          .distance(120)
          .strength(0.5)
      )
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(40))
      .force("x", d3.forceX(width / 2).strength(0.05))
      .force("y", d3.forceY(height / 2).strength(0.05));

    // Draw edges
    const linkGroup = container.append("g").attr("class", "links");

    const link = linkGroup
      .selectAll<SVGLineElement, SimulationEdge>("line")
      .data(edgeData)
      .join("line")
      .attr("stroke", "#334155")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.6)
      .attr("marker-end", "url(#arrowhead)")
      .style("transition", "stroke-opacity 0.3s ease");

    // Edge labels
    const linkLabels = container
      .append("g")
      .attr("class", "link-labels")
      .selectAll<SVGTextElement, SimulationEdge>("text")
      .data(edgeData)
      .join("text")
      .attr("font-size", "9px")
      .attr("fill", "#64748b")
      .attr("text-anchor", "middle")
      .attr("dy", -4)
      .text((d) => EDGE_LABELS[d.edge_type] || d.edge_type)
      .style("pointer-events", "none")
      .style("opacity", 0);

    // Draw nodes
    const nodeGroup = container.append("g").attr("class", "nodes");

    const node = nodeGroup
      .selectAll<SVGGElement, SimulationNode>("g")
      .data(nodeData)
      .join("g")
      .attr("class", "node")
      .style("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, SimulationNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Node circles with glow
    node
      .append("circle")
      .attr("r", (d) => (d.node_type === "patient" ? 24 : 16))
      .attr("fill", (d) => NODE_CONFIG[d.node_type]?.color || "#94a3b8")
      .attr("stroke", (d) => NODE_CONFIG[d.node_type]?.glow || "#64748b")
      .attr("stroke-width", 2)
      .attr("filter", "url(#glow)")
      .style("transition", "all 0.3s ease");

    // Negation indicator (strike-through effect)
    node
      .filter((d) => Boolean(d.properties?.is_negated))
      .append("line")
      .attr("x1", -12)
      .attr("y1", 0)
      .attr("x2", 12)
      .attr("y2", 0)
      .attr("stroke", "#ef4444")
      .attr("stroke-width", 2)
      .attr("stroke-linecap", "round");

    // Node labels
    node
      .append("text")
      .attr("dy", (d) => (d.node_type === "patient" ? 38 : 30))
      .attr("text-anchor", "middle")
      .attr("fill", "#e2e8f0")
      .attr("font-size", (d) => (d.node_type === "patient" ? "12px" : "10px"))
      .attr("font-weight", (d) => (d.node_type === "patient" ? "600" : "400"))
      .text((d) => {
        const maxLen = 16;
        return d.label.length > maxLen ? d.label.slice(0, maxLen) + "…" : d.label;
      })
      .style("pointer-events", "none")
      .style("text-shadow", "0 1px 3px rgba(0,0,0,0.8)");

    // Node interactions
    node
      .on("mouseenter", function (event, d) {
        setHoveredNode(d);
        setTooltipPos({ x: event.pageX, y: event.pageY });

        // Highlight node
        d3.select(this)
          .select("circle")
          .attr("filter", "url(#glow-selected)")
          .attr("stroke-width", 3);

        // Show connected edge labels
        linkLabels.style("opacity", (l) => {
          const source = typeof l.source === "object" ? l.source.id : l.source;
          const target = typeof l.target === "object" ? l.target.id : l.target;
          return source === d.id || target === d.id ? 1 : 0;
        });
      })
      .on("mousemove", (event) => {
        setTooltipPos({ x: event.pageX, y: event.pageY });
      })
      .on("mouseleave", function (_, d) {
        setHoveredNode(null);

        if (selectedNode !== d.id) {
          d3.select(this)
            .select("circle")
            .attr("filter", "url(#glow)")
            .attr("stroke-width", 2);
        }

        linkLabels.style("opacity", 0);
      })
      .on("click", function (event, d) {
        event.stopPropagation();
        const newSelected = selectedNode === d.id ? null : d.id;
        setSelectedNode(newSelected);

        // Reset all nodes
        node
          .select("circle")
          .attr("filter", "url(#glow)")
          .attr("stroke-width", 2)
          .style("opacity", 1);

        node.select("text").style("opacity", 1);
        link.attr("stroke-opacity", 0.6);

        if (newSelected) {
          // Get connected node IDs
          const connectedIds = new Set<string>();
          connectedIds.add(newSelected);

          edgeData.forEach((e) => {
            const source = typeof e.source === "object" ? e.source.id : e.source;
            const target = typeof e.target === "object" ? e.target.id : e.target;
            if (source === newSelected) connectedIds.add(target as string);
            if (target === newSelected) connectedIds.add(source as string);
          });

          // Dim non-connected nodes
          node
            .select("circle")
            .style("opacity", (n) => (connectedIds.has(n.id) ? 1 : 0.2));

          node
            .select("text")
            .style("opacity", (n) => (connectedIds.has(n.id) ? 1 : 0.2));

          // Highlight connected edges
          link.attr("stroke-opacity", (l) => {
            const source = typeof l.source === "object" ? l.source.id : l.source;
            const target = typeof l.target === "object" ? l.target.id : l.target;
            return source === newSelected || target === newSelected ? 1 : 0.1;
          });

          // Highlight selected node
          d3.select(this)
            .select("circle")
            .attr("filter", "url(#glow-selected)")
            .attr("stroke-width", 3);
        }
      });

    // Click on background to deselect
    svg.on("click", () => {
      setSelectedNode(null);
      node
        .select("circle")
        .attr("filter", "url(#glow)")
        .attr("stroke-width", 2)
        .style("opacity", 1);
      node.select("text").style("opacity", 1);
      link.attr("stroke-opacity", 0.6);
    });

    // Simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as SimulationNode).x || 0)
        .attr("y1", (d) => (d.source as SimulationNode).y || 0)
        .attr("x2", (d) => (d.target as SimulationNode).x || 0)
        .attr("y2", (d) => (d.target as SimulationNode).y || 0);

      linkLabels
        .attr("x", (d) => {
          const sx = (d.source as SimulationNode).x || 0;
          const tx = (d.target as SimulationNode).x || 0;
          return (sx + tx) / 2;
        })
        .attr("y", (d) => {
          const sy = (d.source as SimulationNode).y || 0;
          const ty = (d.target as SimulationNode).y || 0;
          return (sy + ty) / 2;
        });

      node.attr("transform", (d) => `translate(${d.x || 0},${d.y || 0})`);
    });

    // Initial zoom to fit
    const initialScale = 0.9;
    svg.call(
      zoom.transform,
      d3.zoomIdentity
        .translate(width * (1 - initialScale) / 2, height * (1 - initialScale) / 2)
        .scale(initialScale)
    );

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, dimensions, activeFilters, selectedNode]);

  return (
    <div className="relative w-full h-full min-h-[500px] bg-slate-950 rounded-xl overflow-hidden">
      {/* Subtle grid background */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(148, 163, 184, 0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148, 163, 184, 0.5) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
        }}
      />

      {/* Controls */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-3">
        {/* Legend / Filters */}
        <div className="bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 border border-slate-800">
          <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
            Node Types
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(NODE_CONFIG).map(([type, config]) => {
              const count = nodes.filter((n) => n.node_type === type).length;
              if (count === 0 && type !== "patient") return null;

              const isActive = activeFilters.has(type);
              return (
                <button
                  key={type}
                  onClick={() => toggleFilter(type)}
                  className={`
                    flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium
                    transition-all duration-200 border
                    ${isActive
                      ? "border-slate-600 bg-slate-800"
                      : "border-slate-800 bg-slate-900/50 opacity-50"
                    }
                  `}
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: config.color,
                      boxShadow: isActive ? `0 0 8px ${config.glow}` : "none",
                    }}
                  />
                  <span className="text-slate-300">{config.label}</span>
                  <span className="text-slate-500">({count})</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-slate-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-slate-800">
          <div className="text-[10px] text-slate-500 space-y-0.5">
            <div><span className="text-slate-400">Scroll</span> to zoom</div>
            <div><span className="text-slate-400">Drag</span> to pan / move nodes</div>
            <div><span className="text-slate-400">Click</span> node to highlight connections</div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="absolute top-4 right-4 z-10 bg-slate-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-slate-800">
        <div className="flex items-center gap-4 text-xs">
          <div>
            <span className="text-slate-500">Nodes</span>
            <span className="ml-1.5 text-slate-200 font-semibold tabular-nums">
              {nodes.filter((n) => activeFilters.has(n.node_type)).length}
            </span>
          </div>
          <div className="w-px h-4 bg-slate-700" />
          <div>
            <span className="text-slate-500">Edges</span>
            <span className="ml-1.5 text-slate-200 font-semibold tabular-nums">
              {edges.filter((e) => {
                const sourceNode = nodes.find((n) => n.id === e.source_node_id);
                const targetNode = nodes.find((n) => n.id === e.target_node_id);
                return sourceNode && targetNode &&
                  activeFilters.has(sourceNode.node_type) &&
                  activeFilters.has(targetNode.node_type);
              }).length}
            </span>
          </div>
        </div>
      </div>

      {/* SVG Container */}
      <div ref={containerRef} className="w-full h-full">
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
          className="w-full h-full"
        />
      </div>

      {/* Tooltip */}
      {hoveredNode && (
        <div
          className="fixed z-50 pointer-events-none"
          style={{
            left: tooltipPos.x + 12,
            top: tooltipPos.y - 8,
          }}
        >
          <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-xl px-3 py-2 max-w-xs">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor: NODE_CONFIG[hoveredNode.node_type]?.color,
                  boxShadow: `0 0 6px ${NODE_CONFIG[hoveredNode.node_type]?.glow}`,
                }}
              />
              <span className="text-sm font-semibold text-slate-100">
                {hoveredNode.label}
              </span>
            </div>

            <div className="text-xs text-slate-400 space-y-0.5">
              <div>
                <span className="text-slate-500">Type:</span>{" "}
                <span className="capitalize">{hoveredNode.node_type}</span>
              </div>

              {hoveredNode.omop_concept_id && (
                <div>
                  <span className="text-slate-500">OMOP ID:</span>{" "}
                  <span className="font-mono">{hoveredNode.omop_concept_id}</span>
                </div>
              )}

              {typeof hoveredNode.properties?.assertion === "string" && (
                <div>
                  <span className="text-slate-500">Assertion:</span>{" "}
                  <span className={
                    hoveredNode.properties.assertion === "absent"
                      ? "text-red-400"
                      : hoveredNode.properties.assertion === "possible"
                        ? "text-amber-400"
                        : "text-emerald-400"
                  }>
                    {hoveredNode.properties.assertion}
                  </span>
                </div>
              )}

              {typeof hoveredNode.properties?.temporality === "string" && (
                <div>
                  <span className="text-slate-500">Temporality:</span>{" "}
                  <span>{hoveredNode.properties.temporality}</span>
                </div>
              )}

              {Boolean(hoveredNode.properties?.is_negated) && (
                <div className="text-red-400 font-medium mt-1">
                  ⊘ Negated Finding
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Selected node info */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 right-4 z-10">
          <div className="bg-slate-900/95 backdrop-blur-sm border border-slate-700 rounded-lg px-4 py-3 mx-auto max-w-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {(() => {
                  const node = nodes.find((n) => n.id === selectedNode);
                  if (!node) return null;
                  return (
                    <>
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{
                          backgroundColor: NODE_CONFIG[node.node_type]?.color,
                          boxShadow: `0 0 8px ${NODE_CONFIG[node.node_type]?.glow}`,
                        }}
                      />
                      <span className="text-sm font-semibold text-slate-100">
                        {node.label}
                      </span>
                      <span className="text-xs text-slate-500 capitalize">
                        ({node.node_type})
                      </span>
                    </>
                  );
                })()}
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-500 hover:text-slate-300 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Showing {edges.filter((e) => e.source_node_id === selectedNode || e.target_node_id === selectedNode).length} connections
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
