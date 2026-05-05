"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";

export default function LayoutShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isAuthRoute = pathname?.startsWith("/auth");

  return (
    <div className="min-h-full flex bg-gray-50 text-gray-900">
      {!isAuthRoute && <Sidebar />}
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
