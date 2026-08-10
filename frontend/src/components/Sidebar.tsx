"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { authApi } from "@/lib/auth-api";
import { orgApi } from "@/lib/org-api";
import { workflowApi } from "@/lib/api";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  key?: string;
  adminOnly?: boolean;
  children?: { href: string; label: string; icon: string; key?: string; adminOnly?: boolean }[];
}

interface WorkflowSummary {
  id: string;
  title: string;
  status: string;
  created_at: string;
  selected_skills?: string[];
}

const navItems: NavItem[] = [
  { href: "/chat", label: "AI 会话", icon: "💬", key: "chat" },
  {
    href: "/workflows",
    label: "工作流管理",
    icon: "📊",
    key: "workflows",
    children: [
      { href: "/requirements", label: "需求输入", icon: "📝", key: "workflows.requirements" },
      { href: "/workflows", label: "工作流列表", icon: "📋", key: "workflows.list" },
      { href: "/prototypes", label: "原型预览", icon: "🎨", key: "workflows.prototypes" },
      { href: "/documents", label: "文档查看", icon: "📄", key: "workflows.documents" },
      { href: "/reports", label: "校验报告", icon: "✅", key: "workflows.reports" },
    ],
  },
  { href: "/market-research", label: "市场调研", icon: "🔍", key: "market-research" },
  { href: "/channels", label: "渠道接入", icon: "📡", key: "channels" },
  { href: "/usage", label: "模型用量", icon: "📈", key: "usage" },
  { href: "/skills", label: "PM Skills", icon: "🎯", key: "skills" },
  { href: "/knowledge-base", label: "知识库", icon: "📚", key: "knowledge-base" },
  { href: "/component-library", label: "组件库", icon: "🧩", key: "component-library" },
  {
    href: "/settings",
    label: "系统设置",
    icon: "⚙️",
    key: "settings",
    children: [
      { href: "/memory", label: "记忆管理", icon: "🧠", key: "settings.memory" },
      { href: "/integrations", label: "集成配置", icon: "🔗", key: "settings.integrations" },
      { href: "/settings/llm", label: "供应商配置", icon: "🤖", key: "settings.llm" },
    ],
  },
  {
    href: "/org",
    label: "组织管理",
    icon: "🏢",
    key: "org",
    adminOnly: true,
    children: [
      { href: "/org/groups", label: "用户组管理", icon: "👥", key: "org.groups" },
      { href: "/org/permissions", label: "权限设置", icon: "🔐", key: "org.permissions" },
    ],
  },
];

const STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  failed: "失败",
  running: "运行中",
  init: "初始化",
  parsing: "解析中",
  parsed: "已解析",
  generating: "生成中",
  generated: "已生成",
  verifying: "校验中",
  verified: "已校验",
  waiting_user_input: "等待输入",
  cancelled: "已取消",
};

const STATUS_COLORS: Record<string, string> = {
  completed: "text-green-600",
  failed: "text-red-600",
  running: "text-blue-600",
  init: "text-gray-500",
  parsing: "text-blue-500",
  waiting_user_input: "text-yellow-600",
  cancelled: "text-gray-400",
};

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [expandedItems, setExpandedItems] = useState<string[]>(["/workflows", "/settings"]);
  const [recentWorkflows, setRecentWorkflows] = useState<WorkflowSummary[]>([]);
  const [workflowsLoading, setWorkflowsLoading] = useState(false);
  const [allowedMenuKeys, setAllowedMenuKeys] = useState<string[] | null>(null);
  const [userRole, setUserRole] = useState<string>("member");

  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        const [menuData, userData] = await Promise.all([
          orgApi.getMyMenus(),
          orgApi.getMyMenus().catch(() => null),
        ]);
        setAllowedMenuKeys(menuData.menu_keys);
        const token = localStorage.getItem("pm_access_token");
        if (token) {
          try {
            const payload = JSON.parse(atob(token.split(".")[1]));
            setUserRole(payload.role || "member");
          } catch {}
        }
      } catch {
        setAllowedMenuKeys(null);
      }
    };
    fetchPermissions();
  }, []);

  const filteredNavItems = allowedMenuKeys
    ? navItems.filter((item) => {
        if (item.adminOnly) return userRole === "admin";
        if (!allowedMenuKeys.includes(item.key || item.href.replace("/", ""))) return false;
        if (item.children) {
          const filteredChildren = item.children.filter(
            (child) => allowedMenuKeys.includes(child.key || child.href.replace("/", "")) || child.adminOnly
          );
          return filteredChildren.length > 0;
        }
        return true;
      })
    : navItems.filter((item) => !item.adminOnly);

  // 加载最近工作流
  useEffect(() => {
    if (expandedItems.includes("/workflows")) {
      loadRecentWorkflows();
    }
  }, [expandedItems]);

  const loadRecentWorkflows = async () => {
    setWorkflowsLoading(true);
    try {
      const data = await workflowApi.list({ page: 1, size: 5 });
      if (data && data.workflows) {
        setRecentWorkflows(data.workflows.map((w: { id: string; title?: string; status: string; created_at: string; selected_skills?: string[] }) => ({
          id: w.id,
          title: w.title || "未命名工作流",
          status: w.status,
          created_at: w.created_at,
          selected_skills: w.selected_skills,
        })));
      }
    } catch {
      // 静默失败
    } finally {
      setWorkflowsLoading(false);
    }
  };

  const handleLogout = async () => {
    router.push("/auth/login");
    try {
      await authApi.logout();
    } catch {
      // ignore
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

  const isChildActive = (children: { href: string; }[]) => {
    return children.some((child) => pathname === child.href || pathname.startsWith(`${child.href}/`));
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  };

  const renderNavItem = (item: NavItem) => {
    if (item.children) {
      const visibleChildren = item.children.filter(
        (child) => !child.adminOnly || userRole === "admin"
      );
      if (visibleChildren.length === 0) return null;

      const expanded = expandedItems.includes(item.href);
      const active = isActive(item.href) || isChildActive(visibleChildren);

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
              {visibleChildren.map((child) => (
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
              {/* 最近工作流列表 */}
              {item.href === "/workflows" && (
                <li>
                  <div className="mt-1 pt-1 border-t border-gray-100">
                    {workflowsLoading ? (
                      <div className="px-3 py-2 text-xs text-gray-400">加载中...</div>
                    ) : recentWorkflows.length > 0 ? (
                      <div className="space-y-0.5">
                        <div className="px-3 py-1 text-xs text-gray-400 font-medium">最近工作流</div>
                        {recentWorkflows.map((wf) => (
                          <Link
                            key={wf.id}
                            href={`/workflows/detail?id=${wf.id}`}
                            className={`flex flex-col px-3 py-1.5 rounded text-xs transition-colors ${
                              pathname === `/workflows/detail` && pathname.includes(wf.id)
                                ? "bg-blue-50 text-blue-700"
                                : "text-gray-500 hover:bg-gray-50"
                            }`}
                          >
                            <div className="flex items-center justify-between w-full">
                              <span className="truncate max-w-[120px]">{wf.title}</span>
                              <span className={`shrink-0 ${STATUS_COLORS[wf.status] || "text-gray-400"}`}>
                                {STATUS_LABELS[wf.status] || wf.status}
                              </span>
                            </div>
                            {wf.selected_skills && wf.selected_skills.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {wf.selected_skills.slice(0, 3).map((s) => (
                                  <span key={s} className="px-1 py-0.5 bg-blue-50 text-blue-600 rounded text-[10px] border border-blue-100">
                                    {s}
                                  </span>
                                ))}
                                {wf.selected_skills.length > 3 && (
                                  <span className="text-[10px] text-gray-400">+{wf.selected_skills.length - 3}</span>
                                )}
                              </div>
                            )}
                          </Link>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </li>
              )}
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
      <nav className="flex-1 p-3 overflow-y-auto">
        <ul className="space-y-1">
          {filteredNavItems.map(renderNavItem)}
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
