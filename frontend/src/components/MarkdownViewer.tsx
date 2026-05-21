"use client";

import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ViewMode = "source" | "preview" | "split";

interface MarkdownViewerProps {
  content: string;
  title?: string;
  className?: string;
}

export default function MarkdownViewer({
  content,
  title,
  className = "",
}: MarkdownViewerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("preview");

  const handleExportMarkdown = useCallback(() => {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || "document"}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [content, title]);

  const handleExportHTML = useCallback(() => {
    const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title || "Document"}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.6;
      max-width: 900px;
      margin: 0 auto;
      padding: 2rem;
      color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
      margin-top: 1.5em;
      margin-bottom: 0.5em;
      color: #111;
    }
    h1 { font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }
    h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
    h3 { font-size: 1.25em; }
    p { margin: 1em 0; }
    ul, ol { margin: 1em 0; padding-left: 2em; }
    li { margin: 0.25em 0; }
    code {
      background-color: #f4f4f4;
      padding: 0.2em 0.4em;
      border-radius: 3px;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.9em;
    }
    pre {
      background-color: #f4f4f4;
      padding: 1em;
      border-radius: 5px;
      overflow-x: auto;
    }
    pre code {
      background-color: transparent;
      padding: 0;
    }
    blockquote {
      border-left: 4px solid #ddd;
      margin: 1em 0;
      padding: 0.5em 1em;
      color: #666;
      background-color: #f9f9f9;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 1em 0;
    }
    th, td {
      border: 1px solid #ddd;
      padding: 0.5em 1em;
      text-align: left;
    }
    th {
      background-color: #f4f4f4;
      font-weight: 600;
    }
    tr:nth-child(even) {
      background-color: #f9f9f9;
    }
    a {
      color: #0366d6;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    hr {
      border: none;
      border-top: 2px solid #eee;
      margin: 2em 0;
    }
    img {
      max-width: 100%;
      height: auto;
    }
  </style>
</head>
<body>
${content}
</body>
</html>`;

    const blob = new Blob([htmlContent], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || "document"}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [content, title]);

  const handlePrintPDF = useCallback(() => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;

    const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>${title || "Document"}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.6;
      max-width: 900px;
      margin: 0 auto;
      padding: 2rem;
      color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
      margin-top: 1.5em;
      margin-bottom: 0.5em;
      color: #111;
    }
    h1 { font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }
    h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
    h3 { font-size: 1.25em; }
    p { margin: 1em 0; }
    ul, ol { margin: 1em 0; padding-left: 2em; }
    li { margin: 0.25em 0; }
    code {
      background-color: #f4f4f4;
      padding: 0.2em 0.4em;
      border-radius: 3px;
      font-size: 0.9em;
    }
    pre {
      background-color: #f4f4f4;
      padding: 1em;
      border-radius: 5px;
      overflow-x: auto;
    }
    pre code { background-color: transparent; padding: 0; }
    blockquote {
      border-left: 4px solid #ddd;
      margin: 1em 0;
      padding: 0.5em 1em;
      color: #666;
      background-color: #f9f9f9;
    }
    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
    th, td { border: 1px solid #ddd; padding: 0.5em 1em; text-align: left; }
    th { background-color: #f4f4f4; font-weight: 600; }
    tr:nth-child(even) { background-color: #f9f9f9; }
    a { color: #0366d6; text-decoration: none; }
    hr { border: none; border-top: 2px solid #eee; margin: 2em 0; }
    @media print {
      body { padding: 0; }
      @page { margin: 2cm; }
    }
  </style>
</head>
<body>
${content}
</body>
</html>`;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
    setTimeout(() => {
      printWindow.print();
    }, 500);
  }, [content, title]);

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b">
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setViewMode("source")}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              viewMode === "source"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            源码
          </button>
          <button
            onClick={() => setViewMode("preview")}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              viewMode === "preview"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            预览
          </button>
          <button
            onClick={() => setViewMode("split")}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              viewMode === "split"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            分屏
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleExportMarkdown}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            title="导出 Markdown"
          >
            <svg className="w-4 h-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            .md
          </button>
          <button
            onClick={handleExportHTML}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            title="导出 HTML"
          >
            <svg className="w-4 h-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            .html
          </button>
          <button
            onClick={handlePrintPDF}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            title="导出 PDF"
          >
            <svg className="w-4 h-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            .pdf
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-auto">
        {viewMode === "source" && (
          <pre className="p-4 text-sm font-mono text-gray-800 bg-gray-50 whitespace-pre-wrap break-words">
            {content}
          </pre>
        )}

        {viewMode === "preview" && (
          <div className="p-6 prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}

        {viewMode === "split" && (
          <div className="flex h-full">
            <div className="w-1/2 border-r overflow-auto">
              <pre className="p-4 text-sm font-mono text-gray-800 bg-gray-50 whitespace-pre-wrap break-words">
                {content}
              </pre>
            </div>
            <div className="w-1/2 overflow-auto">
              <div className="p-6 prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
