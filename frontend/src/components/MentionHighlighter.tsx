"use client";

import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";

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

interface MentionHighlighterProps {
  text: string;
  mentions: MentionSpan[];
  onMentionClick?: (mention: MentionSpan) => void;
  selectedMention?: MentionSpan | null;
}

const DOMAIN_COLORS: Record<string, string> = {
  Condition: "bg-red-100 border-red-400 text-red-800 dark:bg-red-900/30 dark:border-red-700 dark:text-red-200",
  Drug: "bg-blue-100 border-blue-400 text-blue-800 dark:bg-blue-900/30 dark:border-blue-700 dark:text-blue-200",
  Measurement: "bg-green-100 border-green-400 text-green-800 dark:bg-green-900/30 dark:border-green-700 dark:text-green-200",
  Procedure: "bg-orange-100 border-orange-400 text-orange-800 dark:bg-orange-900/30 dark:border-orange-700 dark:text-orange-200",
  Observation: "bg-gray-100 border-gray-400 text-gray-800 dark:bg-gray-700/30 dark:border-gray-600 dark:text-gray-200",
};

const ASSERTION_STYLES: Record<string, string> = {
  present: "",
  absent: "line-through opacity-60",
  possible: "border-dashed",
};

export function MentionHighlighter({
  text,
  mentions,
  onMentionClick,
  selectedMention,
}: MentionHighlighterProps) {
  const segments = useMemo(() => {
    if (!mentions.length) {
      return [{ type: "text" as const, content: text }];
    }

    // Sort mentions by start offset
    const sortedMentions = [...mentions].sort((a, b) => a.start_offset - b.start_offset);

    // Remove overlapping mentions (keep first one)
    const nonOverlapping: MentionSpan[] = [];
    let lastEnd = -1;
    for (const m of sortedMentions) {
      if (m.start_offset >= lastEnd) {
        nonOverlapping.push(m);
        lastEnd = m.end_offset;
      }
    }

    const result: Array<
      | { type: "text"; content: string }
      | { type: "mention"; content: string; mention: MentionSpan }
    > = [];

    let currentPos = 0;

    for (const mention of nonOverlapping) {
      // Add text before mention
      if (mention.start_offset > currentPos) {
        result.push({
          type: "text",
          content: text.slice(currentPos, mention.start_offset),
        });
      }

      // Add mention
      result.push({
        type: "mention",
        content: text.slice(mention.start_offset, mention.end_offset),
        mention,
      });

      currentPos = mention.end_offset;
    }

    // Add remaining text
    if (currentPos < text.length) {
      result.push({
        type: "text",
        content: text.slice(currentPos),
      });
    }

    return result;
  }, [text, mentions]);

  return (
    <div className="whitespace-pre-wrap rounded-lg bg-zinc-100 p-4 font-mono text-sm dark:bg-zinc-800 leading-relaxed">
      {segments.map((segment, index) => {
        if (segment.type === "text") {
          return <span key={index}>{segment.content}</span>;
        }

        const mention = segment.mention;
        const domain = mention.domain || "Observation";
        const domainColor = DOMAIN_COLORS[domain] || DOMAIN_COLORS.Observation;
        const assertionStyle = ASSERTION_STYLES[mention.assertion] || "";
        const isSelected =
          selectedMention &&
          selectedMention.start_offset === mention.start_offset &&
          selectedMention.end_offset === mention.end_offset;

        return (
          <span
            key={index}
            className={`
              inline cursor-pointer rounded border px-0.5 transition-all
              ${domainColor}
              ${assertionStyle}
              ${isSelected ? "ring-2 ring-yellow-400 ring-offset-1" : ""}
              hover:ring-2 hover:ring-yellow-300
            `}
            onClick={() => onMentionClick?.(mention)}
            title={`${domain} | ${mention.assertion} | ${(mention.confidence * 100).toFixed(0)}% confidence`}
          >
            {segment.content}
          </span>
        );
      })}
    </div>
  );
}

interface MentionLegendProps {
  className?: string;
}

export function MentionLegend({ className }: MentionLegendProps) {
  return (
    <div className={`flex flex-wrap gap-2 ${className || ""}`}>
      <Badge variant="outline" className="bg-red-100 border-red-400 text-red-800 dark:bg-red-900/30 dark:text-red-200">
        Condition
      </Badge>
      <Badge variant="outline" className="bg-blue-100 border-blue-400 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200">
        Drug
      </Badge>
      <Badge variant="outline" className="bg-green-100 border-green-400 text-green-800 dark:bg-green-900/30 dark:text-green-200">
        Measurement
      </Badge>
      <Badge variant="outline" className="bg-orange-100 border-orange-400 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200">
        Procedure
      </Badge>
      <Badge variant="outline" className="bg-gray-100 border-gray-400 text-gray-800 dark:bg-gray-700/30 dark:text-gray-200">
        Observation
      </Badge>
    </div>
  );
}

interface MentionDetailProps {
  mention: MentionSpan | null;
  className?: string;
}

export function MentionDetail({ mention, className }: MentionDetailProps) {
  if (!mention) {
    return (
      <div className={`text-center text-zinc-500 py-4 ${className || ""}`}>
        Click on a highlighted mention to see details
      </div>
    );
  }

  return (
    <div className={`space-y-2 p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg ${className || ""}`}>
      <div className="font-semibold text-lg">{mention.text}</div>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <dt className="text-zinc-500">Domain</dt>
          <dd className="font-medium">{mention.domain || "Unknown"}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Assertion</dt>
          <dd className="font-medium capitalize">{mention.assertion}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Temporality</dt>
          <dd className="font-medium capitalize">{mention.temporality}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Confidence</dt>
          <dd className="font-medium">{(mention.confidence * 100).toFixed(0)}%</dd>
        </div>
        {mention.section && (
          <div className="col-span-2">
            <dt className="text-zinc-500">Section</dt>
            <dd className="font-medium">{mention.section}</dd>
          </div>
        )}
        <div className="col-span-2">
          <dt className="text-zinc-500">Position</dt>
          <dd className="font-mono text-xs">
            {mention.start_offset}:{mention.end_offset}
          </dd>
        </div>
      </dl>
    </div>
  );
}
