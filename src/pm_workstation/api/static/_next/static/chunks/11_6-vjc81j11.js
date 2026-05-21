(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(["object"==typeof document?document.currentScript:void 0,64850,e=>{"use strict";var t=e.i(48277),r=e.i(30668),o=e.i(35827),a=e.i(59925);e.s(["default",0,function({content:e,title:l,className:i=""}){let[n,s]=(0,r.useState)("preview"),d=(0,r.useCallback)(()=>{let t=new Blob([e],{type:"text/markdown;charset=utf-8"}),r=URL.createObjectURL(t),o=document.createElement("a");o.href=r,o.download=`${l||"document"}.md`,document.body.appendChild(o),o.click(),document.body.removeChild(o),URL.revokeObjectURL(r)},[e,l]),c=(0,r.useCallback)(()=>{let t=new Blob([`<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${l||"Document"}</title>
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
${e}
</body>
</html>`],{type:"text/html;charset=utf-8"}),r=URL.createObjectURL(t),o=document.createElement("a");o.href=r,o.download=`${l||"document"}.html`,document.body.appendChild(o),o.click(),document.body.removeChild(o),URL.revokeObjectURL(r)},[e,l]),m=(0,r.useCallback)(()=>{let t=window.open("","_blank");if(!t)return;let r=`<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>${l||"Document"}</title>
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
${e}
</body>
</html>`;t.document.write(r),t.document.close(),setTimeout(()=>{t.print()},500)},[e,l]);return(0,t.jsxs)("div",{className:`flex flex-col h-full ${i}`,children:[(0,t.jsxs)("div",{className:"flex items-center justify-between px-4 py-2 bg-gray-50 border-b",children:[(0,t.jsxs)("div",{className:"flex items-center space-x-1",children:[(0,t.jsx)("button",{onClick:()=>s("source"),className:`px-3 py-1.5 text-sm rounded-md transition-colors ${"source"===n?"bg-white text-gray-900 shadow-sm":"text-gray-600 hover:text-gray-900 hover:bg-gray-100"}`,children:"源码"}),(0,t.jsx)("button",{onClick:()=>s("preview"),className:`px-3 py-1.5 text-sm rounded-md transition-colors ${"preview"===n?"bg-white text-gray-900 shadow-sm":"text-gray-600 hover:text-gray-900 hover:bg-gray-100"}`,children:"预览"}),(0,t.jsx)("button",{onClick:()=>s("split"),className:`px-3 py-1.5 text-sm rounded-md transition-colors ${"split"===n?"bg-white text-gray-900 shadow-sm":"text-gray-600 hover:text-gray-900 hover:bg-gray-100"}`,children:"分屏"})]}),(0,t.jsxs)("div",{className:"flex items-center space-x-2",children:[(0,t.jsxs)("button",{onClick:d,className:"px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors",title:"导出 Markdown",children:[(0,t.jsx)("svg",{className:"w-4 h-4 inline-block mr-1",fill:"none",viewBox:"0 0 24 24",stroke:"currentColor",children:(0,t.jsx)("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"})}),".md"]}),(0,t.jsxs)("button",{onClick:c,className:"px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors",title:"导出 HTML",children:[(0,t.jsx)("svg",{className:"w-4 h-4 inline-block mr-1",fill:"none",viewBox:"0 0 24 24",stroke:"currentColor",children:(0,t.jsx)("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"})}),".html"]}),(0,t.jsxs)("button",{onClick:m,className:"px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors",title:"导出 PDF",children:[(0,t.jsx)("svg",{className:"w-4 h-4 inline-block mr-1",fill:"none",viewBox:"0 0 24 24",stroke:"currentColor",children:(0,t.jsx)("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"})}),".pdf"]})]})]}),(0,t.jsxs)("div",{className:"flex-1 overflow-auto",children:["source"===n&&(0,t.jsx)("pre",{className:"p-4 text-sm font-mono text-gray-800 bg-gray-50 whitespace-pre-wrap break-words",children:e}),"preview"===n&&(0,t.jsx)("div",{className:"p-6 prose prose-sm max-w-none",children:(0,t.jsx)(o.default,{remarkPlugins:[a.default],children:e})}),"split"===n&&(0,t.jsxs)("div",{className:"flex h-full",children:[(0,t.jsx)("div",{className:"w-1/2 border-r overflow-auto",children:(0,t.jsx)("pre",{className:"p-4 text-sm font-mono text-gray-800 bg-gray-50 whitespace-pre-wrap break-words",children:e})}),(0,t.jsx)("div",{className:"w-1/2 overflow-auto",children:(0,t.jsx)("div",{className:"p-6 prose prose-sm max-w-none",children:(0,t.jsx)(o.default,{remarkPlugins:[a.default],children:e})})})]})]})]})}])},84074,e=>{"use strict";var t=e.i(48277),r=e.i(30668),o=e.i(16506),a=e.i(1831),l=e.i(64850);e.s(["default",0,function(){let[e,i]=(0,r.useState)([]),[n,s]=(0,r.useState)(!0),[d,c]=(0,r.useState)(null),[m,h]=(0,r.useState)(""),[x,u]=(0,r.useState)(!1);return((0,r.useEffect)(()=>{!async function(){try{let e=(await a.workflowApi.list()).workflows.filter(e=>e.prd_document_url&&["completed","verified","verifying"].includes(e.status));i(e),e.length>0&&c(e[0])}catch{}finally{s(!1)}}()},[]),(0,r.useEffect)(()=>{!async function(){if(!d?.prd_document_url)return h("");u(!0);try{let e=await fetch(d.prd_document_url),t=await e.text();h(t)}catch{h("文档加载失败")}finally{u(!1)}}()},[d?.prd_document_url]),n)?(0,t.jsx)("div",{className:"flex items-center justify-center h-64",children:(0,t.jsx)("p",{className:"text-gray-500",children:"加载中..."})}):(0,t.jsxs)("div",{children:[(0,t.jsx)("h1",{className:"text-2xl font-bold mb-6",children:"产品文档"}),0===e.length?(0,t.jsxs)("div",{className:"text-center py-12 bg-white rounded-lg border border-gray-200",children:[(0,t.jsx)("p",{className:"text-gray-500",children:"暂无可用的产品文档"}),(0,t.jsx)(o.default,{href:"/requirements",className:"mt-2 inline-block text-blue-600 hover:underline text-sm",children:"创建新工作流 →"})]}):(0,t.jsxs)("div",{className:"flex gap-6 h-[calc(100vh-8rem)]",children:[(0,t.jsxs)("div",{className:"w-64 bg-white rounded-lg border border-gray-200 p-3 overflow-auto",children:[(0,t.jsx)("h2",{className:"text-sm font-medium text-gray-700 mb-3",children:"文档列表"}),(0,t.jsx)("ul",{className:"space-y-2",children:e.map(e=>(0,t.jsx)("li",{children:(0,t.jsxs)("button",{onClick:()=>c(e),className:`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${d?.id===e.id?"bg-blue-50 text-blue-700":"hover:bg-gray-50"}`,children:[(0,t.jsx)("div",{className:"font-medium truncate",children:e.requirement_text?.slice(0,30)||e.title||"未命名需求"}),(0,t.jsx)("div",{className:"text-xs text-gray-400 mt-0.5",children:new Date(e.updated_at).toLocaleDateString("zh-CN")})]})},e.id))})]}),(0,t.jsx)("div",{className:"flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden",children:x?(0,t.jsx)("div",{className:"flex items-center justify-center h-full",children:(0,t.jsx)("p",{className:"text-gray-500",children:"文档加载中..."})}):m?(0,t.jsx)(l.default,{content:m,title:d?.requirement_text?.slice(0,30)||d?.title||"产品文档"}):d?(0,t.jsx)("div",{className:"flex items-center justify-center h-full",children:(0,t.jsx)("p",{className:"text-gray-500",children:"文档生成中，请稍候..."})}):(0,t.jsx)("div",{className:"flex items-center justify-center h-full",children:(0,t.jsx)("p",{className:"text-gray-500",children:"请选择一个文档"})})})]})]})}])}]);