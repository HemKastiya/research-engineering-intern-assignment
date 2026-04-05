"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { EmbeddingsResult } from "@/lib/api";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import EmptyState from "@/components/ui/EmptyState";

const CLUSTER_COLORS = [
  "#D81B60",
  "#1E88E5",
  "#43A047",
  "#F4511E",
  "#8E24AA",
  "#00897B",
  "#C62828",
  "#3949AB",
  "#7CB342",
  "#5E35B1",
  "#039BE5",
  "#FB8C00",
  "#6D4C41",
  "#00ACC1",
  "#EF5350",
  "#AB47BC",
  "#26A69A",
  "#FF7043",
  "#42A5F5",
  "#66BB6A",
  "#EC407A",
  "#7E57C2",
  "#26C6DA",
  "#9E9D24",
];
const OUTLIER_LABEL = -1;
const OUTLIER_COLOR = "#9EA3A8";
const GOLDEN_ANGLE = 137.508;

function clamp01(value: number | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) return 0.75;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function clusterColor(label: number): string {
  if (label === OUTLIER_LABEL) return OUTLIER_COLOR;
  if (label >= 0 && label < CLUSTER_COLORS.length) {
    return CLUSTER_COLORS[label];
  }

  // Deterministic high-contrast fallback for larger cluster counts.
  const hue = (Math.abs(label) * GOLDEN_ANGLE) % 360;
  const saturation = 82;
  // Darken yellow hues for better visibility on light backgrounds.
  const lightness = hue > 48 && hue < 72 ? 36 : 44;
  return `hsl(${hue.toFixed(0)} ${saturation}% ${lightness}%)`;
}

interface ScatterPlotProps {
  data: EmbeddingsResult | null;
  isLoading?: boolean;
  titles?: Record<string, string>;
  showOutliers?: boolean;
}

export default function ScatterPlot({ data, isLoading, titles, showOutliers = true }: ScatterPlotProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const { umap_2d, cluster_labels, post_ids, point_labels, point_confidences } = data;
    if (!umap_2d?.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth || 640;
    const height = svgRef.current.clientHeight || 480;
    const margin = { top: 16, right: 16, bottom: 32, left: 32 };

    const xs = umap_2d.map((p) => p[0]);
    const ys = umap_2d.map((p) => p[1]);

    const xScale = d3
      .scaleLinear()
      .domain([d3.min(xs)!, d3.max(xs)! + 0.5])
      .range([margin.left, width - margin.right]);

    const yScale = d3
      .scaleLinear()
      .domain([d3.min(ys)! - 0.5, d3.max(ys)! + 0.5])
      .range([height - margin.bottom, margin.top]);

    svg
      .append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(xScale).ticks(5).tickSize(0))
      .select(".domain")
      .attr("stroke", "#D4CFC6");

    svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(yScale).ticks(5).tickSize(0))
      .select(".domain")
      .attr("stroke", "#D4CFC6");

    const g = svg.append("g");
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 20])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoom);

    const points = umap_2d
      .map((coords, index) => ({ coords, index }))
      .filter((point) => showOutliers || (cluster_labels[point.index] ?? OUTLIER_LABEL) !== OUTLIER_LABEL);

    g.selectAll("circle")
      .data(points)
      .enter()
      .append("circle")
      .attr("cx", (d) => xScale(d.coords[0]))
      .attr("cy", (d) => yScale(d.coords[1]))
      .attr("r", (d) => ((cluster_labels[d.index] ?? OUTLIER_LABEL) === OUTLIER_LABEL ? 3 : 4))
      .attr("fill", (d) => {
        const label = cluster_labels[d.index] ?? OUTLIER_LABEL;
        return clusterColor(label);
      })
      .attr("fill-opacity", (d) => {
        const label = cluster_labels[d.index] ?? OUTLIER_LABEL;
        if (label === OUTLIER_LABEL) return 0.24;
        const confidence = clamp01(point_confidences?.[d.index]);
        return 0.35 + confidence * 0.5;
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.8)
      .style("cursor", "pointer")
      .on("mouseenter", function (event, d) {
        const idx = d.index;
        const postId = post_ids?.[idx];
        const pointLabel = point_labels?.[idx];
        const label = cluster_labels[idx] ?? OUTLIER_LABEL;
        const confidence = point_confidences?.[idx];
        const confidenceText =
          typeof confidence === "number" && Number.isFinite(confidence)
            ? ` | confidence ${(confidence * 100).toFixed(0)}%`
            : "";
        const prefix = label === OUTLIER_LABEL ? "Outlier" : `Cluster ${label}`;
        const title = `${prefix}: ${pointLabel ?? titles?.[postId] ?? postId ?? "Post"}${confidenceText}`;
        d3.select(this)
          .attr("r", label === OUTLIER_LABEL ? 5 : 7)
          .attr("fill-opacity", label === OUTLIER_LABEL ? 0.45 : 1);
        setTooltip({ x: event.offsetX + 12, y: event.offsetY - 8, text: title });
      })
      .on("mouseleave", function (_, d) {
        const label = cluster_labels[d.index] ?? OUTLIER_LABEL;
        const confidence = clamp01(point_confidences?.[d.index]);
        d3.select(this)
          .attr("r", label === OUTLIER_LABEL ? 3 : 4)
          .attr("fill-opacity", label === OUTLIER_LABEL ? 0.24 : 0.35 + confidence * 0.5);
        setTooltip(null);
      });
  }, [data, titles, showOutliers]);

  if (isLoading) return <LoadingSkeleton variant="chart" />;
  if (!data || !data.umap_2d?.length) {
    return (
      <EmptyState
        title="Embeddings not yet built"
        description="Embeddings are still processing. Check back shortly or trigger ingest from overview."
      />
    );
  }

  const visibleLabels = showOutliers
    ? data.cluster_labels
    : data.cluster_labels.filter((label) => label !== OUTLIER_LABEL);
  const uniqueLabels = [...new Set(visibleLabels)].sort((a, b) => a - b);
  const labelCounts = visibleLabels.reduce<Record<number, number>>((acc, label) => {
    acc[label] = (acc[label] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="relative h-[520px] w-full">
      <svg ref={svgRef} className="h-full w-full" />
      {tooltip && (
        <div
          className="press-card press-card-brief pointer-events-none absolute z-10 max-w-[200px] px-2 py-1 text-xs"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}
      <div className="press-card press-card-brief absolute right-2 top-2 space-y-1 p-2">
        {uniqueLabels.map((label) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: clusterColor(label) }}
            />
            <span className="data-label">
              {label === OUTLIER_LABEL ? "Outliers" : `Cluster ${label}`} ({labelCounts[label] ?? 0})
            </span>
          </div>
        ))}
        <p className="byline pt-1">Point opacity encodes cluster confidence.</p>
      </div>
    </div>
  );
}
