"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { EmbeddingsResult } from "@/lib/api";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import EmptyState from "@/components/ui/EmptyState";

const CLUSTER_COLORS = [
  "#C41E1E", "#30363F", "#7B6A58", "#8B5C2C",
  "#5E4A7E", "#2E6171", "#7F1D1D", "#4A5568",
];

interface ScatterPlotProps {
  data: EmbeddingsResult | null;
  isLoading?: boolean;
  titles?: Record<string, string>;
}

export default function ScatterPlot({ data, isLoading, titles }: ScatterPlotProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const { umap_2d, cluster_labels, post_ids, point_labels } = data;
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
      .domain([d3.min(xs)! - 0.5, d3.max(xs)! + 0.5])
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

    const points = umap_2d.map((coords, index) => ({ coords, index }));

    g.selectAll("circle")
      .data(points)
      .enter()
      .append("circle")
      .attr("cx", (d) => xScale(d.coords[0]))
      .attr("cy", (d) => yScale(d.coords[1]))
      .attr("r", 4)
      .attr("fill", (d) => {
        const label = cluster_labels[d.index] ?? 0;
        const paletteIdx = ((label % CLUSTER_COLORS.length) + CLUSTER_COLORS.length) % CLUSTER_COLORS.length;
        return CLUSTER_COLORS[paletteIdx];
      })
      .attr("fill-opacity", 0.76)
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.8)
      .style("cursor", "pointer")
      .on("mouseenter", function (event, d) {
        const idx = d.index;
        const postId = post_ids?.[idx];
        const pointLabel = point_labels?.[idx];
        const title = pointLabel ?? titles?.[postId] ?? postId ?? "Post";
        d3.select(this).attr("r", 7).attr("fill-opacity", 1);
        setTooltip({ x: event.offsetX + 12, y: event.offsetY - 8, text: title });
      })
      .on("mouseleave", function () {
        d3.select(this).attr("r", 4).attr("fill-opacity", 0.76);
        setTooltip(null);
      });
  }, [data, titles]);

  if (isLoading) return <LoadingSkeleton variant="chart" />;
  if (!data || !data.umap_2d?.length) {
    return (
      <EmptyState
        title="Embeddings not yet built"
        description="Embeddings are still processing. Check back shortly or trigger ingest from overview."
      />
    );
  }

  const uniqueLabels = [...new Set(data.cluster_labels)].sort((a, b) => a - b);

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
        {uniqueLabels.slice(0, 8).map((label) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: CLUSTER_COLORS[label % CLUSTER_COLORS.length] }}
            />
            <span className="data-label">Cluster {label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
