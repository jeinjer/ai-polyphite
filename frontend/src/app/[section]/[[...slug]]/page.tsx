import { notFound } from "next/navigation";

import { Dashboard } from "@/components/dashboard";
import type { DashboardSection } from "@/stores/ui-store";

const sections = new Set<DashboardSection>([
  "predictions",
  "trades",
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
    (slug.length > 0 && section !== "predictions")
  ) {
    notFound();
  }
  return <Dashboard />;
}
