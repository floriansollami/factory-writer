import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import type { RecentPack } from "@/features/style-guide/schema";

const columns: ColumnDef<RecentPack>[] = [
  {
    accessorKey: "version",
    header: "Version",
    cell: ({ row }) => (
      <div>
        <p className="font-semibold text-[var(--color-ink)]">{row.original.version}</p>
        <p className="mt-1 text-xs text-[var(--color-muted)]">{row.original.documentSourcePdf}</p>
      </div>
    ),
  },
  {
    accessorKey: "status",
    header: "Statut",
    cell: ({ row }) => {
      const status = row.original.status;
      const tone = status === "ACTIF" ? "success" : "neutral";

      return <Badge tone={tone}>{packStatusLabel(status)}</Badge>;
    },
  },
  {
    accessorKey: "rulesCount",
    header: "Règles",
    cell: ({ row }) => <span className="font-semibold">{row.original.rulesCount}</span>,
  },
  {
    accessorKey: "approvedRulesCount",
    header: "Approuvées",
    cell: ({ row }) => <span className="font-semibold">{row.original.approvedRulesCount}</span>,
  },
  {
    accessorKey: "disabledRulesCount",
    header: "Écartées",
    cell: ({ row }) => <span className="font-semibold">{row.original.disabledRulesCount}</span>,
  },
  {
    accessorKey: "approvedBy",
    header: "Approbation",
    cell: ({ row }) => row.original.approvedBy ?? "Non approuvé",
  },
  {
    accessorKey: "updatedAt",
    header: "Dernière mise à jour",
  },
];

export function RecentPacksTable({
  packs,
  onRowClick,
}: {
  packs: RecentPack[];
  onRowClick?: (pack: RecentPack) => void;
}) {
  const table = useReactTable({
    data: packs,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="overflow-hidden rounded-[1.5rem] bg-white/70">
      <table className="w-full border-separate border-spacing-0 text-left text-sm">
        <thead className="bg-[var(--color-surface-raised)] text-xs uppercase tracking-[0.14em] text-[var(--color-muted)]">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-5 py-4 font-bold">
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={
                onRowClick
                  ? "align-top text-[var(--color-ink)] transition hover:bg-[var(--color-sage-soft)]/60 cursor-pointer focus-visible:bg-[var(--color-sage-soft)]/60 focus-visible:outline-none"
                  : "align-top text-[var(--color-ink)] transition hover:bg-[var(--color-sage-soft)]/60"
              }
              onClick={onRowClick ? () => onRowClick(row.original) : undefined}
              onKeyDown={
                onRowClick
                  ? (event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onRowClick(row.original);
                      }
                    }
                  : undefined
              }
              role={onRowClick ? "button" : undefined}
              tabIndex={onRowClick ? 0 : undefined}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-5 py-4">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function packStatusLabel(status: RecentPack["status"]) {
  if (status === "ACTIF") {
    return "Actif";
  }
  if (status === "ARCHIVE") {
    return "Archivé";
  }
  return "À relire";
}
