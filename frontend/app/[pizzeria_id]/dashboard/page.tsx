"use client";

import { useParams } from "next/navigation";
import KanbanBoard from "@/components/kanban/KanbanBoard";

export default function DashboardPage() {
  const { pizzeria_id } = useParams<{ pizzeria_id: string }>();

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 57px)" }}>
      <KanbanBoard pizzeriaId={pizzeria_id} />
    </div>
  );
}
