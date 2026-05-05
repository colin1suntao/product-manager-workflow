"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/requirements", label: "需求输入", icon: "📝" },
  { href: "/workflows", label: "流程监控", icon: "📊" },
  { href: "/prototypes", label: "原型预览", icon: "🎨" },
  { href: "/documents", label: "文档查看", icon: "📄" },
  { href: "/reports", label: "校验报告", icon: "✅" },
  { href: "/components-lib", label: "组件库", icon: "🧩" },
  { href: "/integrations", label: "集成配置", icon: "⚙️" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 min-h-screen bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-lg font-bold text-gray-900">PM Workstation</h1>
        <p className="text-xs text-gray-500 mt-1">多Agent协作工作站</p>
      </div>
      <nav className="flex-1 p-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <span className="text-base">{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-400">v0.1.0</p>
      </div>
    </aside>
  );
}
