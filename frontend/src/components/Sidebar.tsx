"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { authApi } from "@/lib/auth-api";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  children?: { href: string; label: string; icon: string }[];
}

const navItems: NavItem[] = [
  { href: "/chat", label: "AI 会话", icon: "💬" },
  {
    href: "/workflows",
    label: "工作流管理",
    icon: "📊",
    children: [
      { href: "/requirements", label: "需求输入", icon: "📝" },
      { href: "/prototypes", label: "原型预览", icon: "🎨" },
      { href: "/documents", label: "文档查看", icon: "📄" },
      { href: "/reports", label: "校验报告", icon: "✅" },
    ],
  },
  { href: "/market-research", label: "市场调研", icon: "🔍" },
  { href: "/skills", label: "PM Skills", icon: "🎯" },
  { href: "/components-lib", label: "组件库", icon: "🧩" },
  {
    href: "/settings",
    label: "系统设置",
    icon: "⚙️",
    children: [
      { href: "/memory", label: "记忆管理", icon: "🧠" },
      { href: "/integrations", label: "集成配置", icon: "🔗" },
      { href: "/settings/llm", label: "供应商配置", icon: "🤖" },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [expandedItems, setExpandedItems] = useState<string[]>(["/workflows", "/settings"]);

  const handleLogout = async () => {
    // 先跳转到登录页，避免其他组件继续调用 API
    router.push("/auth/login");

    // 然后在后台执行登出操作
    try {
      await authApi.logout();
    } catch {
      // 即使登出失败，也已经跳转了
    }
  };

  const toggleExpanded = (href: string) => {
    setExpandedItems((prev) =>
      prev.includes(href) ? prev.filter((item) => item !== href) : [...prev, href]
    );
  };

  const isActive = (href: string) => {
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const isChildActive = (children: { href: string }[]) => {
    return children.some((child) => pathname === child.href || pathname.startsWith(`${child.href}/`));
  };

  const renderNavItem = (item: NavItem) => {
    if (item.children) {
      const expanded = expandedItems.includes(item.href);
      const active = isActive(item.href) || isChildActive(item.children);

      return (
        <li key={item.href}>
          <button
            onClick={() => toggleExpanded(item.href)}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              active ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-base">{item.icon}</span>
              {item.label}
            </div>
            <svg
              className={`w-4 h-4 transition-transform ${expanded ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
          {expanded && (
            <ul className="ml-4 mt-1 space-y-1">
              {item.children.map((child) => (
                <li key={child.href}>
                  <Link
                    href={child.href}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive(child.href)
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    <span className="text-sm">{child.icon}</span>
                    {child.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </li>
      );
    }

    return (
      <li key={item.href}>
        <Link
          href={item.href}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            isActive(item.href) ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          <span className="text-base">{item.icon}</span>
          {item.label}
        </Link>
      </li>
    );
  };

  return (
    <aside className="w-56 min-h-screen bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-lg font-bold text-gray-900">PM Workstation</h1>
        <p className="text-xs text-gray-500 mt-1">多Agent协作工作站</p>
      </div>
      <nav className="flex-1 p-3">
        <ul className="space-y-1">
          {navItems.map(renderNavItem)}
        </ul>
      </nav>
      <div className="p-3 border-t border-gray-200 space-y-1">
        <Link
          href="/settings/profile"
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            pathname === "/settings/profile"
              ? "bg-blue-50 text-blue-700"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          <span className="text-base">👤</span>
          个人中心
        </Link>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
        >
          <span className="text-base">🚪</span>
          退出登录
        </button>
      </div>
    </aside>
  );
}
