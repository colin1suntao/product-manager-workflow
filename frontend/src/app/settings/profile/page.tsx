"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/auth-api";

export default function ProfilePage() {
  const router = useRouter();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);

    if (!oldPassword || !newPassword || !confirmPassword) {
      setMessage({ type: "error", text: "请填写所有字段" });
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "两次输入的新密码不一致" });
      return;
    }

    if (newPassword.length < 8) {
      setMessage({ type: "error", text: "新密码至少需要 8 个字符" });
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
      });
      setMessage({ type: "success", text: "密码修改成功，请重新登录" });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");

      // 3 秒后跳转到登录页
      setTimeout(() => {
        authApi.logout();
        router.push("/auth/login");
      }, 3000);
    } catch (err) {
      setMessage({ type: "error", text: err instanceof Error ? err.message : "修改失败" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">个人中心</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">修改密码</h2>

        {message && (
          <div
            className={`mb-4 p-3 rounded-lg ${
              message.type === "success"
                ? "bg-green-50 border border-green-200 text-green-700"
                : "bg-red-50 border border-red-200 text-red-700"
            }`}
          >
            {message.text}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              当前密码
            </label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md"
              placeholder="请输入当前密码"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              新密码
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md"
              placeholder="至少 8 个字符"
              minLength={8}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              确认新密码
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md"
              placeholder="再次输入新密码"
              minLength={8}
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "修改中..." : "修改密码"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
