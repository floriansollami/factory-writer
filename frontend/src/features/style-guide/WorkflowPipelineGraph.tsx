import "@xyflow/react/dist/style.css";

import {
  Background,
  BackgroundVariant,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export type WorkflowGraphStep = {
  id: string;
  label: string;
  description: string;
  status: "completed" | "running" | "pending" | "failed";
  eta?: string;
};

type WorkflowNodeData = Record<string, unknown> & {
  stepNumber: number;
  label: string;
  description: string;
  eta: string | null;
  status: WorkflowGraphStep["status"];
};

type WorkflowGraphNodeModel = Node<WorkflowNodeData, "workflowStep">;
type WorkflowGraphEdgeModel = Edge<Record<string, never>, "smoothstep">;

const WORKFLOW_NODE_WIDTH = 232;
const WORKFLOW_NODE_GAP = 96;

const workflowGraphNodeTypes = {
  workflowStep: WorkflowGraphNode,
};

export default function WorkflowPipelineGraph({ steps }: { steps: WorkflowGraphStep[] }) {
  const graph = buildWorkflowGraph(steps);

  return (
    <ReactFlow
      nodes={graph.nodes}
      edges={graph.edges}
      nodeTypes={workflowGraphNodeTypes}
      fitView
      fitViewOptions={{ padding: 0.16 }}
      minZoom={0.55}
      maxZoom={1.1}
      nodesDraggable={false}
      nodesConnectable={false}
      edgesFocusable={false}
      elementsSelectable={false}
      panOnDrag={false}
      zoomOnScroll={false}
      zoomOnPinch={false}
      zoomOnDoubleClick={false}
      preventScrolling={false}
      proOptions={{ hideAttribution: true }}
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={22}
        size={1}
        color="rgba(104,113,106,0.28)"
      />
    </ReactFlow>
  );
}

function WorkflowGraphNode({ data }: NodeProps<WorkflowGraphNodeModel>) {
  const statusLabel = workflowStepStatusLabel(data.status);

  return (
    <div
      className={cn(
        "relative w-[232px] rounded-[1.4rem] border p-4 shadow-[0_18px_42px_rgba(27,28,26,0.10)] backdrop-blur-sm",
        data.status === "completed" && "border-[rgba(23,49,36,0.18)] bg-[rgba(255,253,248,0.96)]",
        data.status === "running" && "border-[rgba(141,77,50,0.32)] bg-[rgba(255,250,240,0.98)]",
        data.status === "pending" && "border-[rgba(231,227,218,0.95)] bg-[rgba(255,255,255,0.84)]",
        data.status === "failed" && "border-[rgba(159,39,39,0.28)] bg-[rgba(255,245,242,0.98)]",
      )}
      aria-current={data.status === "running" ? "step" : undefined}
      aria-label={`${data.label}: ${statusLabel}`}
    >
      <Handle
        className="!size-2 !border-0 !bg-transparent"
        type="target"
        position={Position.Left}
        isConnectable={false}
      />
      <Handle
        className="!size-2 !border-0 !bg-transparent"
        type="source"
        position={Position.Right}
        isConnectable={false}
      />

      <div className="flex items-start justify-between gap-3">
        <span
          className={cn(
            "grid size-10 shrink-0 place-items-center rounded-2xl text-sm font-bold",
            data.status === "completed" && "bg-[var(--color-forest)] text-white",
            data.status === "running" && "bg-[var(--color-gold)] text-[var(--color-ink)]",
            data.status === "pending" && "bg-[var(--color-stone)] text-[var(--color-muted)]",
            data.status === "failed" && "bg-[var(--color-error)] text-white",
          )}
        >
          {data.status === "completed" ? <CheckCircle2 className="size-5" /> : null}
          {data.status === "running" ? <Loader2 className="size-5 animate-spin" /> : null}
          {data.status === "failed" ? "!" : null}
          {data.status === "pending" ? data.stepNumber : null}
        </span>

        <span
          className={cn(
            "rounded-full px-3 py-1 text-[0.68rem] font-bold uppercase tracking-[0.12em]",
            data.status === "completed" && "bg-[var(--color-sage-soft)] text-[var(--color-forest)]",
            data.status === "running" && "bg-[var(--color-gold-soft)] text-[var(--color-teak)]",
            data.status === "pending" && "bg-[var(--color-surface-raised)] text-[var(--color-muted)]",
            data.status === "failed" && "bg-[var(--color-error-soft)] text-[var(--color-error)]",
          )}
        >
          {statusLabel}
        </span>
      </div>

      <p className="mt-5 text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
        Étape {data.stepNumber}
      </p>
      <p className="mt-2 font-serif text-xl font-semibold leading-tight tracking-[-0.035em] text-[var(--color-ink)]">
        {data.label}
      </p>
      <p className="mt-3 line-clamp-2 text-sm leading-6 text-[var(--color-muted)]">{data.description}</p>
      {data.eta && data.status === "running" ? (
        <p className="mt-3 text-xs font-semibold text-[var(--color-teak)]">{data.eta}</p>
      ) : null}
    </div>
  );
}

function buildWorkflowGraph(
  steps: WorkflowGraphStep[],
): { nodes: WorkflowGraphNodeModel[]; edges: WorkflowGraphEdgeModel[] } {
  const nodes: WorkflowGraphNodeModel[] = steps.map((step, index) => ({
    id: step.id,
    type: "workflowStep",
    position: {
      x: index * (WORKFLOW_NODE_WIDTH + WORKFLOW_NODE_GAP),
      y: 0,
    },
    data: {
      stepNumber: index + 1,
      label: step.label,
      description: step.description,
      eta: step.eta ?? null,
      status: step.status,
    },
    draggable: false,
    selectable: false,
    style: {
      width: WORKFLOW_NODE_WIDTH,
    },
  }));

  const edges: WorkflowGraphEdgeModel[] = steps.slice(0, -1).map((step, index) => {
    const nextStep = steps[index + 1];
    const isActiveEdge = step.status === "completed" && nextStep?.status === "running";
    const isCompletedEdge = step.status === "completed" && nextStep?.status === "completed";
    const stroke = isActiveEdge
      ? "var(--color-teak)"
      : isCompletedEdge
        ? "var(--color-forest)"
        : "var(--color-stone)";

    return {
      id: `${step.id}-${nextStep.id}`,
      source: step.id,
      target: nextStep.id,
      type: "smoothstep",
      animated: isActiveEdge,
      interactionWidth: 18,
      selectable: false,
      style: {
        stroke,
        strokeWidth: isActiveEdge ? 3 : 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: stroke,
        width: 18,
        height: 18,
      },
    };
  });

  return { nodes, edges };
}

function workflowStepStatusLabel(status: WorkflowGraphStep["status"]) {
  if (status === "completed") {
    return "Terminé";
  }
  if (status === "running") {
    return "En cours";
  }
  if (status === "failed") {
    return "Erreur";
  }
  return "À venir";
}
