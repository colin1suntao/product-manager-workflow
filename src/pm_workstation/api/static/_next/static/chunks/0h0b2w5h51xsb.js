(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(["object"==typeof document?document.currentScript:void 0,64850,e=>{"use strict";var t=e.i(48277),r=e.i(30668),s=e.i(35827),a=e.i(59925);e.s(["default",0,function({content:e,title:l,className:o=""}){let[d,i]=(0,r.useState)("preview"),n=(0,r.useCallback)(()=>{let t=new Blob([e],{type:"text/markdown;charset=utf-8"}),r=URL.createObjectURL(t),s=document.createElement("a");s.href=r,s.download=`${l||"document"}.md`,document.body.appendChild(s),s.click(),document.body.removeChild(s),URL.revokeObjectURL(r)},[e,l]),c=(0,r.useCallback)(()=>{let t=new Blob([`<!DOCTYPE html>
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
</html>`],{type:"text/html;charset=utf-8"}),r=URL.createObjectURL(t),s=document.createElement("a");s.href=r,s.download=`${l||"document"}.html`,document.body.appendChild(s),s.click(),document.body.removeChild(s),URL.revokeObjectURL(r)},[e,l]),m=(0,r.useCallback)(()=>{let t=window.open("","_blank");if(!t)return;let r=`<!DOCTYPE html>
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
</html>`;t.document.write(r),t.document.close(),setTimeout(()=>{t.print()},500)},[e,l]);return(0,t.jsxs)("div",{className:`flex flex-col h-full ${o}`,children:[(0,t.jsxs)("div",{className:"flex items-center justify-between px-4 py-2 bg-gray-50 border-b",children:[(0,t.jsxs)("div",{className:"flex items-center space-x-1",children:[(0,t.jsx)("button",{onClick:()=>i("source"),className:`px-3 py-1.5 text-sm rounded-md transition-colors ${"source"===d?"bg-white text-gray-900 shadow-sm":"text-gray-600 hover:text-gray-900 hover:bg-gray-100"}`,children:"源码"}),(0,t.jsx)("button",{onClick:()=>i("preview"),className:`px-3 py-1.5 text-sm rounded-md transition-colors ${"preview"===d?"bg-white text-gray-900 shadow-sm":"text-gray-600 hover:text-gray-900 hover:bg-gray-100"}`,children:"预览"}),(0,t.jsx)("button",{onClick:()=>i("split"),className:`px-3 py-1.5 text-sm rounded-md transition-colors ${"split"===d?"bg-white text-gray-900 shadow-sm":"text-gray-600 hover:text-gray-900 hover:bg-gray-100"}`,children:"分屏"})]}),(0,t.jsxs)("div",{className:"flex items-center space-x-2",children:[(0,t.jsxs)("button",{onClick:n,className:"px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors",title:"导出 Markdown",children:[(0,t.jsx)("svg",{className:"w-4 h-4 inline-block mr-1",fill:"none",viewBox:"0 0 24 24",stroke:"currentColor",children:(0,t.jsx)("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"})}),".md"]}),(0,t.jsxs)("button",{onClick:c,className:"px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors",title:"导出 HTML",children:[(0,t.jsx)("svg",{className:"w-4 h-4 inline-block mr-1",fill:"none",viewBox:"0 0 24 24",stroke:"currentColor",children:(0,t.jsx)("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"})}),".html"]}),(0,t.jsxs)("button",{onClick:m,className:"px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors",title:"导出 PDF",children:[(0,t.jsx)("svg",{className:"w-4 h-4 inline-block mr-1",fill:"none",viewBox:"0 0 24 24",stroke:"currentColor",children:(0,t.jsx)("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"})}),".pdf"]})]})]}),(0,t.jsxs)("div",{className:"flex-1 overflow-auto",children:["source"===d&&(0,t.jsx)("pre",{className:"p-4 text-sm font-mono text-gray-800 bg-gray-50 whitespace-pre-wrap break-words",children:e}),"preview"===d&&(0,t.jsx)("div",{className:"p-6 prose prose-sm max-w-none",children:(0,t.jsx)(s.default,{remarkPlugins:[a.default],children:e})}),"split"===d&&(0,t.jsxs)("div",{className:"flex h-full",children:[(0,t.jsx)("div",{className:"w-1/2 border-r overflow-auto",children:(0,t.jsx)("pre",{className:"p-4 text-sm font-mono text-gray-800 bg-gray-50 whitespace-pre-wrap break-words",children:e})}),(0,t.jsx)("div",{className:"w-1/2 overflow-auto",children:(0,t.jsx)("div",{className:"p-6 prose prose-sm max-w-none",children:(0,t.jsx)(s.default,{remarkPlugins:[a.default],children:e})})})]})]})]})}])},56691,e=>{"use strict";var t=e.i(48277),r=e.i(30668),s=e.i(1831),a=e.i(64850);let l={macro:"宏观环境",market:"市场规模",customer:"用户研究",competitor:"竞争分析",strategy:"产品策略",other:"其他"},o={macro:"bg-blue-100 text-blue-700 border-blue-300",market:"bg-green-100 text-green-700 border-green-300",customer:"bg-purple-100 text-purple-700 border-purple-300",competitor:"bg-orange-100 text-orange-700 border-orange-300",strategy:"bg-pink-100 text-pink-700 border-pink-300",other:"bg-gray-100 text-gray-700 border-gray-300"};e.s(["default",0,function(){let[e,d]=(0,r.useState)("create"),[i,n]=(0,r.useState)(""),[c,m]=(0,r.useState)(""),[x,h]=(0,r.useState)([]),[g,u]=(0,r.useState)([]),[b,p]=(0,r.useState)([]),[y,f]=(0,r.useState)([]),[v,j]=(0,r.useState)(!1),[w,N]=(0,r.useState)(""),[k,C]=(0,r.useState)(""),[S,R]=(0,r.useState)(null),[L,$]=(0,r.useState)(""),[z,T]=(0,r.useState)(null),[_,M]=(0,r.useState)(!1),[U,A]=(0,r.useState)(""),[B,F]=(0,r.useState)("");(0,r.useEffect)(()=>{P(),H()},[]);let P=async()=>{try{let e=await s.marketResearchApi.list();p(e.reports)}catch(e){console.error("Failed to load reports:",e)}},H=async()=>{try{let e=await s.marketResearchApi.listTemplates();f(e.templates)}catch(e){console.error("Failed to load templates:",e)}},O=async()=>{if(!c.trim())return void N("请输入调研需求描述");j(!0),N("");try{let e=await s.marketResearchApi.recommendSkills(c);u(e.recommendations),h(e.recommendations.map(e=>e.name))}catch(e){N("获取技能推荐失败"),console.error(e)}finally{j(!1)}},D=async()=>{if(!c.trim())return void N("请输入调研需求描述");if(0===x.length)return void N("请选择至少一个 PM Skills");j(!0),N(""),C("");try{let e=await s.marketResearchApi.create({title:i||void 0,requirement_text:c,selected_skills:x});C(`调研任务已创建，报告 ID: ${e.report_id}`),R(e.report_id),T("pending"),E(e.report_id),P()}catch(e){N("创建调研任务失败"),console.error(e)}finally{j(!1)}},E=async e=>{let t=0,r=async()=>{if(t>=60)return void T("timeout");try{let a=await s.marketResearchApi.getStatus(e);if(T(a.status),"completed"===a.status){let t=await s.marketResearchApi.get(e);$(t.report_content),P();return}if("failed"===a.status)return void N(`报告生成失败: ${a.error_message}`);t++,setTimeout(r,2e3)}catch(e){console.error("Failed to poll status:",e),t++,setTimeout(r,2e3)}};r()},V=async e=>{R(e),j(!0);try{let t=await s.marketResearchApi.get(e);$(t.report_content),T(t.status)}catch(e){N("加载报告失败"),console.error(e)}finally{j(!1)}},W=async()=>{if(!U.trim())return void N("请输入模板名称");if(0===x.length)return void N("请选择至少一个技能");try{await s.marketResearchApi.saveTemplate({name:U,description:B,skill_names:x}),C("模板保存成功"),M(!1),A(""),F(""),H()}catch(e){N("保存模板失败"),console.error(e)}},q=async e=>{try{await s.marketResearchApi.deleteTemplate(e),H()}catch(e){N("删除模板失败"),console.error(e)}};return(0,t.jsx)("div",{className:"min-h-screen bg-gray-50",children:(0,t.jsxs)("div",{className:"max-w-7xl mx-auto px-4 py-8",children:[(0,t.jsx)("h1",{className:"text-3xl font-bold text-gray-900 mb-8",children:"市场调研"}),(0,t.jsxs)("div",{className:"flex space-x-4 mb-6",children:[(0,t.jsx)("button",{onClick:()=>d("create"),className:`px-4 py-2 rounded-lg ${"create"===e?"bg-blue-600 text-white":"bg-white text-gray-700 hover:bg-gray-100"}`,children:"创建调研"}),(0,t.jsxs)("button",{onClick:()=>d("history"),className:`px-4 py-2 rounded-lg ${"history"===e?"bg-blue-600 text-white":"bg-white text-gray-700 hover:bg-gray-100"}`,children:["历史报告 (",b.length,")"]}),(0,t.jsxs)("button",{onClick:()=>d("templates"),className:`px-4 py-2 rounded-lg ${"templates"===e?"bg-blue-600 text-white":"bg-white text-gray-700 hover:bg-gray-100"}`,children:["调研模板 (",y.length,")"]})]}),w&&(0,t.jsx)("div",{className:"mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700",children:w}),k&&(0,t.jsx)("div",{className:"mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700",children:k}),"create"===e&&(0,t.jsxs)("div",{className:"grid grid-cols-1 lg:grid-cols-2 gap-6",children:[(0,t.jsxs)("div",{className:"bg-white rounded-lg shadow p-6",children:[(0,t.jsx)("h2",{className:"text-xl font-semibold mb-4",children:"调研需求"}),(0,t.jsxs)("div",{className:"mb-4",children:[(0,t.jsx)("label",{className:"block text-sm font-medium text-gray-700 mb-2",children:"调研标题（可选）"}),(0,t.jsx)("input",{type:"text",value:i,onChange:e=>n(e.target.value),placeholder:"例如：智能家居市场调研",className:"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})]}),(0,t.jsxs)("div",{className:"mb-4",children:[(0,t.jsx)("label",{className:"block text-sm font-medium text-gray-700 mb-2",children:"调研需求描述 *"}),(0,t.jsx)("textarea",{value:c,onChange:e=>m(e.target.value),placeholder:"请描述您的调研需求，例如： - 分析中国智能家居市场的规模和增长趋势 - 研究目标用户群体的特征和需求 - 评估主要竞争对手的市场策略",rows:6,className:"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})]}),(0,t.jsx)("button",{onClick:O,disabled:v||!c.trim(),className:"w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed",children:v?"分析中...":"智能推荐技能"})]}),(0,t.jsxs)("div",{className:"bg-white rounded-lg shadow p-6",children:[(0,t.jsxs)("div",{className:"flex justify-between items-center mb-4",children:[(0,t.jsx)("h2",{className:"text-xl font-semibold",children:"选择 PM Skills"}),x.length>0&&(0,t.jsx)("button",{onClick:()=>M(!0),className:"px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700",children:"保存为模板"})]}),g.length>0?(0,t.jsx)("div",{className:"space-y-3",children:g.map(e=>(0,t.jsxs)("div",{onClick:()=>{var t;return t=e.name,void h(e=>e.includes(t)?e.filter(e=>e!==t):[...e,t])},className:`p-3 border rounded-lg cursor-pointer transition-all ${x.includes(e.name)?"border-blue-500 bg-blue-50":"border-gray-200 hover:border-gray-300"}`,children:[(0,t.jsxs)("div",{className:"flex justify-between items-start",children:[(0,t.jsxs)("div",{children:[(0,t.jsx)("div",{className:"font-medium text-gray-900",children:e.name}),(0,t.jsx)("div",{className:"text-sm text-gray-600 mt-1",children:e.description})]}),(0,t.jsxs)("div",{className:"flex items-center space-x-2",children:[(0,t.jsx)("span",{className:`px-2 py-1 text-xs rounded ${o[e.category]||o.other}`,children:l[e.category]||e.category}),(0,t.jsx)("div",{className:`w-5 h-5 rounded border-2 flex items-center justify-center ${x.includes(e.name)?"bg-blue-600 border-blue-600":"border-gray-300"}`,children:x.includes(e.name)&&(0,t.jsx)("svg",{className:"w-3 h-3 text-white",fill:"none",viewBox:"0 0 24 24",stroke:"currentColor",children:(0,t.jsx)("path",{strokeLinecap:"round",strokeLinejoin:"round",strokeWidth:2,d:"M5 13l4 4L19 7"})})})]})]}),(0,t.jsxs)("div",{className:"text-xs text-gray-400 mt-2",children:["相关度: ",Math.round(100*e.relevance_score),"%"]})]},e.name))}):(0,t.jsx)("div",{className:"text-center text-gray-500 py-8",children:"请输入调研需求并点击「智能推荐技能」"}),x.length>0&&(0,t.jsxs)("div",{className:"mt-4 pt-4 border-t",children:[(0,t.jsxs)("div",{className:"text-sm text-gray-600 mb-2",children:["已选择 ",x.length," 个技能"]}),(0,t.jsx)("button",{onClick:D,disabled:v,className:"w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50",children:v?"创建中...":"开始生成调研报告"})]})]}),S&&(0,t.jsxs)("div",{className:"lg:col-span-2 bg-white rounded-lg shadow p-6",children:[(0,t.jsx)("h2",{className:"text-xl font-semibold mb-4",children:"调研报告"}),"pending"===z||"running"===z?(0,t.jsxs)("div",{className:"text-center py-8",children:[(0,t.jsx)("div",{className:"animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"}),(0,t.jsx)("p",{className:"text-gray-600",children:"报告生成中，请稍候..."})]}):"completed"===z&&L?(0,t.jsx)("div",{className:"h-[600px] border rounded-lg overflow-hidden",children:(0,t.jsx)(a.default,{content:L,title:i||"市场调研报告"})}):"failed"===z?(0,t.jsx)("div",{className:"text-center py-8 text-red-600",children:"报告生成失败"}):null]})]}),"history"===e&&(0,t.jsxs)("div",{className:"bg-white rounded-lg shadow",children:[0===b.length?(0,t.jsx)("div",{className:"text-center py-12 text-gray-500",children:"暂无调研报告"}):(0,t.jsx)("div",{className:"divide-y",children:b.map(e=>(0,t.jsx)("div",{onClick:()=>V(e.id),className:"p-4 hover:bg-gray-50 cursor-pointer",children:(0,t.jsxs)("div",{className:"flex justify-between items-start",children:[(0,t.jsxs)("div",{children:[(0,t.jsx)("h3",{className:"font-medium text-gray-900",children:e.title}),(0,t.jsxs)("div",{className:"text-sm text-gray-600 mt-1",children:["使用技能: ",e.selected_skills.join(", ")]}),(0,t.jsxs)("div",{className:"text-xs text-gray-400 mt-1",children:["创建时间: ",new Date(e.created_at).toLocaleString()]})]}),(0,t.jsx)("span",{className:`px-2 py-1 text-xs rounded ${"completed"===e.status?"bg-green-100 text-green-700":"failed"===e.status?"bg-red-100 text-red-700":"bg-yellow-100 text-yellow-700"}`,children:"completed"===e.status?"已完成":"failed"===e.status?"失败":"进行中"})]})},e.id))}),S&&L&&(0,t.jsxs)("div",{className:"border-t p-6",children:[(0,t.jsx)("h3",{className:"text-lg font-semibold mb-4",children:"报告内容"}),(0,t.jsx)("div",{className:"h-[600px] border rounded-lg overflow-hidden",children:(0,t.jsx)(a.default,{content:L,title:b.find(e=>e.id===S)?.title||"市场调研报告"})})]})]}),"templates"===e&&(0,t.jsx)("div",{className:"bg-white rounded-lg shadow",children:0===y.length?(0,t.jsx)("div",{className:"text-center py-12 text-gray-500",children:"暂无调研模板，请先创建调研并保存为模板"}):(0,t.jsx)("div",{className:"divide-y",children:y.map(e=>(0,t.jsx)("div",{className:"p-4",children:(0,t.jsxs)("div",{className:"flex justify-between items-start",children:[(0,t.jsxs)("div",{children:[(0,t.jsx)("h3",{className:"font-medium text-gray-900",children:e.name}),e.description&&(0,t.jsx)("div",{className:"text-sm text-gray-600 mt-1",children:e.description}),(0,t.jsxs)("div",{className:"text-sm text-gray-500 mt-2",children:["包含技能: ",e.skill_names.join(", ")]})]}),(0,t.jsxs)("div",{className:"flex space-x-2",children:[(0,t.jsx)("button",{onClick:()=>{h(e.skill_names),d("create"),C(`已加载模板: ${e.name}`)},className:"px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700",children:"使用"}),(0,t.jsx)("button",{onClick:()=>q(e.id),className:"px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700",children:"删除"})]})]})},e.id))})}),_&&(0,t.jsx)("div",{className:"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50",children:(0,t.jsxs)("div",{className:"bg-white rounded-lg p-6 w-full max-w-md",children:[(0,t.jsx)("h3",{className:"text-lg font-semibold mb-4",children:"保存调研模板"}),(0,t.jsxs)("div",{className:"mb-4",children:[(0,t.jsx)("label",{className:"block text-sm font-medium text-gray-700 mb-2",children:"模板名称 *"}),(0,t.jsx)("input",{type:"text",value:U,onChange:e=>A(e.target.value),placeholder:"例如：市场进入分析模板",className:"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})]}),(0,t.jsxs)("div",{className:"mb-4",children:[(0,t.jsx)("label",{className:"block text-sm font-medium text-gray-700 mb-2",children:"模板描述（可选）"}),(0,t.jsx)("textarea",{value:B,onChange:e=>F(e.target.value),placeholder:"描述此模板的适用场景",rows:3,className:"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})]}),(0,t.jsx)("div",{className:"mb-4",children:(0,t.jsxs)("div",{className:"text-sm text-gray-600",children:["已选择技能: ",x.join(", ")]})}),(0,t.jsxs)("div",{className:"flex justify-end space-x-3",children:[(0,t.jsx)("button",{onClick:()=>M(!1),className:"px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200",children:"取消"}),(0,t.jsx)("button",{onClick:W,className:"px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700",children:"保存"})]})]})})]})})}])}]);