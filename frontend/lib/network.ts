import { NetworkEdge, NetworkGraphType } from "@/types";

const DAMPING = 0.85;
const MAX_ITERATIONS = 80;
const EPSILON = 1e-8;

function isDirected(graphType: NetworkGraphType): boolean {
  return graphType === "crosspost";
}

export function computePageRank(
  nodeIds: string[],
  edges: NetworkEdge[],
  graphType: NetworkGraphType
): Record<string, number> {
  const n = nodeIds.length;
  if (n === 0) return {};

  const directed = isDirected(graphType);
  const index = new Map<string, number>();
  nodeIds.forEach((nodeId, i) => index.set(nodeId, i));

  const incoming: Array<Array<{ from: number; weight: number }>> = Array.from(
    { length: n },
    () => []
  );
  const outWeight = new Array<number>(n).fill(0);

  for (const edge of edges) {
    const sourceIdx = index.get(edge.source);
    const targetIdx = index.get(edge.target);
    if (sourceIdx == null || targetIdx == null) continue;
    if (sourceIdx === targetIdx) continue;

    const weight = Math.max(0, edge.weight ?? 1);
    if (weight === 0) continue;

    incoming[targetIdx].push({ from: sourceIdx, weight });
    outWeight[sourceIdx] += weight;

    if (!directed) {
      incoming[sourceIdx].push({ from: targetIdx, weight });
      outWeight[targetIdx] += weight;
    }
  }

  let ranks = new Array<number>(n).fill(1 / n);
  const teleport = (1 - DAMPING) / n;

  for (let iteration = 0; iteration < MAX_ITERATIONS; iteration += 1) {
    const next = new Array<number>(n).fill(teleport);

    let danglingMass = 0;
    for (let i = 0; i < n; i += 1) {
      if (outWeight[i] === 0) {
        danglingMass += ranks[i];
      }
    }
    const danglingContribution = (DAMPING * danglingMass) / n;

    for (let target = 0; target < n; target += 1) {
      let score = danglingContribution;
      for (const edge of incoming[target]) {
        const denom = outWeight[edge.from];
        if (denom > 0) {
          score += DAMPING * (ranks[edge.from] * edge.weight) / denom;
        }
      }
      next[target] += score;
    }

    let delta = 0;
    for (let i = 0; i < n; i += 1) {
      delta += Math.abs(next[i] - ranks[i]);
    }
    ranks = next;
    if (delta < EPSILON) break;
  }

  const sum = ranks.reduce((acc, value) => acc + value, 0);
  const norm = sum > 0 ? sum : 1;

  const result: Record<string, number> = {};
  nodeIds.forEach((nodeId, i) => {
    result[nodeId] = ranks[i] / norm;
  });
  return result;
}
