import { notFound } from "next/navigation";

import { Dashboard } from "@/components/dashboard";
import type { DashboardSection } from "@/stores/ui-store";

const sections = new Set<DashboardSection>([
  "markets",
  "history",
  "predictions",
  "agents",
  "portfolio",
  "trades",
  "positions",
  "performance",
  "experiments",
  "sources",
  "system",
  "settings",
]);

export default async function DashboardRoute({
  params,
}: Readonly<{
  params: Promise<{ section: string; slug?: string[] }>;
}>) {
  const { section, slug = [] } = await params;
  if (
    !sections.has(section as DashboardSection) ||
    slug.length > 1 ||
    (slug.length > 0 &&
      section !== "markets" &&
      section !== "predictions")
  ) {
    notFound();
  }
  return <Dashboard />;
}
