"""LangGraph 工作流图定义

定义工作流状态机的节点和边，实现完整的状态转换流程。
"""

import asyncio
from datetime import datetime, timezone
from typing import Literal

from langgraph.graph import END, START, StateGraph

from pm_workstation.agents.prd_generator import PRDGenerator
from pm_workstation.models.core import VerificationReport, WorkflowStatus
from pm_workstation.orchestrator.workflow_state import WorkflowState


class WorkflowNodes:
    """工作流节点定义

    每个节点对应一个工作流阶段，执行相应的处理逻辑。
    """

    @staticmethod
    def parsing_node(state: WorkflowState, llm_handler=None) -> dict:
        """需求解析节点 (PARSING -> PARSED)

        将原始需求文本解析为结构化需求，超时则跳过解析。
        """
        state.update_status(WorkflowStatus.PARSING)

        try:
            if not state.workflow_run.requirement_text:
                raise ValueError("需求文本为空")

            if llm_handler:
                # 使用 LLM 进行需求解析，超时则跳过
                try:
                    result = WorkflowNodes._call_llm_sync(
                        llm_handler, "parsing", state.workflow_run.requirement_text
                    )
                    if result:
                        state.structured_requirement = result
                        if hasattr(result, 'clarifications') and result.clarifications:
                            state.clarification_questions = [
                                {"id": i, "question": q.question, "context": q.context, "options": q.options}
                                for i, q in enumerate(result.clarifications)
                            ]
                except Exception as e:
                    # LLM 调用失败或超时，跳过解析
                    print(f"[ParsingNode] LLM parsing failed: {e}")
                    pass

            # 如果存在澄清问题，进入等待用户输入
            if state.clarification_questions:
                state.update_status(WorkflowStatus.WAITING_USER_INPUT)
                return {"workflow_run": state.workflow_run, "clarification_questions": state.clarification_questions}

            state.update_status(WorkflowStatus.PARSED)
            return {"workflow_run": state.workflow_run}

        except Exception as e:
            state.error_message = str(e)
            state.update_status(WorkflowStatus.FAILED)
            return {"workflow_run": state.workflow_run, "error_message": state.error_message}

    @staticmethod
    def _call_llm_sync(llm_handler, task: str, requirement_text: str):
        """同步调用 LLM，带超时控制"""
        import threading
        import time

        result_holder = {"value": None, "error": None, "started": False}

        def _run_async():
            """在新线程中创建独立事件循环运行异步代码"""
            try:
                result_holder["started"] = True
                if task == "parsing":
                    from pm_workstation.agents.requirement_parser import RequirementParser
                    parser = RequirementParser(llm_handler=llm_handler)
                    coro = parser.parse(requirement_text)
                elif task == "prototype":
                    from pm_workstation.agents.prototype_generator import PrototypeGenerator
                    gen = PrototypeGenerator(llm_handler=llm_handler)
                    coro = gen.generate(requirement_text)
                elif task == "prd":
                    from pm_workstation.agents.prd_generator import PRDGenerator
                    gen = PRDGenerator(llm_handler=llm_handler)
                    coro = gen.generate(requirement_text)
                else:
                    result_holder["error"] = ValueError(f"Unknown task: {task}")
                    return

                result_holder["value"] = asyncio.run(coro)
            except Exception as e:
                result_holder["error"] = e

        print(f"[LLM] Starting {task} call...")
        start_time = time.time()
        
        thread = threading.Thread(target=_run_async, daemon=True)
        thread.start()
        thread.join(timeout=90)  # 90秒超时（原型和PRD各90秒，加上parsing 60秒，总计不超过3分钟）

        elapsed = time.time() - start_time
        
        if thread.is_alive():
            print(f"[LLM] {task} call timed out after {elapsed:.1f}s")
            raise TimeoutError(f"LLM {task} call timed out after {elapsed:.1f}s")
        
        if result_holder["error"]:
            print(f"[LLM] {task} call failed after {elapsed:.1f}s: {result_holder['error']}")
            raise result_holder["error"]
        
        print(f"[LLM] {task} call completed in {elapsed:.1f}s")
        return result_holder["value"]

    @staticmethod
    def generating_node(state: WorkflowState, llm_handler=None) -> dict:
        """原型与文档生成节点 (PARSED -> GENERATING -> GENERATED)

        通过 LLM 生成原型和 PRD 文档，超时则回退到简单模板。
        """
        state.update_status(WorkflowStatus.GENERATING)

        try:
            req_text = state.workflow_run.requirement_text
            if not req_text:
                raise ValueError("缺少需求文本，无法生成")

            if llm_handler:
                # 使用 LLM 生成原型和文档，超时则回退到简单模板
                llm_ok = True

                # 生成原型（90 秒超时）
                try:
                    print(f"[GeneratingNode] Calling LLM for prototype...")
                    prototype_html = WorkflowNodes._call_llm_sync(
                        llm_handler, "prototype", req_text
                    )
                    if prototype_html:
                        state.prototype_html = prototype_html
                except Exception as e:
                    print(f"[GeneratingNode] Prototype generation failed: {e}")
                    llm_ok = False

                # 生成 PRD（90 秒超时，与原型并行）
                try:
                    print(f"[GeneratingNode] Calling LLM for PRD...")
                    prd_document = WorkflowNodes._call_llm_sync(
                        llm_handler, "prd", req_text
                    )
                    if prd_document:
                        state.prd_document = prd_document
                except Exception as e:
                    print(f"[GeneratingNode] PRD generation failed: {e}")
                    llm_ok = False

                # 如果 LLM 生成失败，使用简单模板兜底
                if not state.prototype_html:
                    state.prototype_html = WorkflowNodes._generate_simple_prototype(req_text)
                if not state.prd_document:
                    state.prd_document = WorkflowNodes._generate_simple_prd(req_text)
            else:
                # 无 LLM 时使用简单模板
                state.prototype_html = WorkflowNodes._generate_simple_prototype(req_text)
                state.prd_document = WorkflowNodes._generate_simple_prd(req_text)

            state.update_status(WorkflowStatus.GENERATED)
            return {
                "workflow_run": state.workflow_run,
                "prototype_html": state.prototype_html,
                "prd_document": state.prd_document,
            }

        except Exception as e:
            state.error_message = str(e)
            state.update_status(WorkflowStatus.FAILED)
            return {"workflow_run": state.workflow_run, "error_message": state.error_message}

    @staticmethod
    def _generate_with_llm_sync(llm_handler, requirement_text: str, structured_requirement=None) -> dict:
        """同步包装器：在同步上下文中调用异步 LLM 生成"""
        import concurrent.futures
        import threading

        results = {"prototype_html": None, "prd_document": None, "error": None}

        def _run_proto():
            try:
                from pm_workstation.agents.huashu_prototype_generator import HuashuPrototypeGenerator
                gen = HuashuPrototypeGenerator(llm_handler=llm_handler)
                results["prototype_html"] = asyncio.run(gen.generate(requirement_text, structured_requirement))
            except Exception as e:
                results["error"] = e

        def _run_prd():
            try:
                from pm_workstation.agents.prd_generator import PRDGenerator
                gen = PRDGenerator(llm_handler=llm_handler)
                results["prd_document"] = asyncio.run(gen.generate(requirement_text, structured_requirement))
            except Exception as e:
                if not results.get("error"):
                    results["error"] = e

        t1 = threading.Thread(target=_run_proto, daemon=True)
        t2 = threading.Thread(target=_run_prd, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=180)
        t2.join(timeout=180)

        if results["error"]:
            raise results["error"]
        return {
            "prototype_html": results["prototype_html"] or "",
            "prd_document": results["prd_document"] or "",
        }

    @staticmethod
    async def _generate_with_llm(llm_handler, requirement_text: str, structured_requirement=None) -> dict:
        """使用 LLM 生成原型和文档"""
        from pm_workstation.agents.huashu_prototype_generator import HuashuPrototypeGenerator
        
        proto_gen = HuashuPrototypeGenerator(llm_handler=llm_handler)
        prd_gen = PRDGenerator(llm_handler=llm_handler)

        prototype_task = proto_gen.generate(requirement_text, structured_requirement)
        prd_task = prd_gen.generate(requirement_text, structured_requirement)

        prototype_html, prd_document = await asyncio.gather(prototype_task, prd_task)

        return {
            "prototype_html": prototype_html,
            "prd_document": prd_document,
        }

    @staticmethod
    def _generate_simple_prototype(req_text: str) -> str:
        """生成简单的 HTML 原型（无 LLM 时的兜底方案，使用 huashu-design 技术栈）"""
        title = req_text.split("\n\n")[0] if "\n\n" in req_text else req_text[:50]
        
        # 分析需求文本，提取关键词
        keywords = []
        if "博客" in req_text or "blog" in req_text.lower():
            keywords = ["文章管理", "评论系统", "用户注册", "分类标签"]
        elif "电商" in req_text or "商城" in req_text or "shop" in req_text.lower():
            keywords = ["商品展示", "购物车", "订单管理", "支付系统"]
        elif "记账" in req_text or "财务" in req_text:
            keywords = ["收支记录", "分类统计", "报表导出", "预算管理"]
        else:
            keywords = ["用户管理", "数据处理", "报表分析", "系统设置"]
        
        sidebar_items = "".join([f'<a class="sidebar-item" href="#" onclick="showSection(\'{kw}\')"><span class="icon">{kw[0]}</span>{kw}</a>' for kw in keywords])
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://unpkg.com/react@18.3.1/umd/react.development.js" integrity="sha384-hD6/rw4ppMLGNu3tX5cjIb+uRZ7UkRJ6BPkLpg4hAu/6onKUg4lLsHAs9EBPT82L" crossorigin="anonymous"></script>
    <script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js" integrity="sha384-u6aeetuaXnQ38mYT8rp6sbXaQe3NL9t+IBXmnYxwkUI2Hw4bsp2Wvmx4yRQF1uAm" crossorigin="anonymous"></script>
    <script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js" integrity="sha384-m08KidiNqLdpJqLq95G/LEi8Qvjl/xUYll3QILypMoQ65QorJ9Lvtp2RXYGBFj1y" crossorigin="anonymous"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; background: #f5f5f5; }}
        
        /* 布局 */
        .navbar {{ background: #001529; color: white; padding: 0 24px; height: 64px; display: flex; align-items: center; justify-content: space-between; position: fixed; width: 100%; top: 0; z-index: 100; }}
        .navbar .logo {{ font-size: 20px; font-weight: bold; }}
        .navbar .user-info {{ display: flex; align-items: center; gap: 16px; font-size: 14px; }}
        
        .sidebar {{ width: 256px; background: white; position: fixed; top: 64px; left: 0; bottom: 0; border-right: 1px solid #e8e8e8; padding: 16px 0; overflow-y: auto; }}
        .sidebar-item {{ display: flex; align-items: center; gap: 12px; padding: 12px 24px; color: #333; text-decoration: none; transition: all 0.2s; }}
        .sidebar-item:hover {{ background: #f5f5f5; }}
        .sidebar-item.active {{ background: #e6f7ff; color: #1890ff; border-right: 3px solid #1890ff; }}
        .sidebar-item .icon {{ width: 32px; height: 32px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; }}
        
        .main {{ margin-left: 256px; margin-top: 64px; padding: 24px; min-height: calc(100vh - 64px); }}
        .card {{ background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .card h2 {{ font-size: 18px; margin-bottom: 16px; color: #333; }}
        .card p {{ color: #666; line-height: 1.6; }}
        
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .stat-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .stat-card .number {{ font-size: 32px; font-weight: bold; color: #1890ff; }}
        .stat-card .label {{ font-size: 14px; color: #999; margin-top: 8px; }}
        
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; padding: 12px 16px; border-bottom: 2px solid #e8e8e8; font-weight: 600; color: #333; }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #f0f0f0; color: #666; }}
        tr:hover {{ background: #fafafa; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        const {{ useState }} = React;
        
        const appData = {{
            title: "{title}",
            keywords: {keywords},
        }};
        
        function App() {{
            const [activeSection, setActiveSection] = useState(appData.keywords[0] || '概览');
            
            return (
                <div>
                    <div className="navbar">
                        <div className="logo">{{appData.title}}</div>
                        <div className="user-info">
                            <span>管理员</span>
                            <div style={{{{width: 32, height: 32, background: '#1890ff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center'}}}}>A</div>
                        </div>
                    </div>
                    
                    <div className="sidebar">
                        {{appData.keywords.map(kw => (
                            <a 
                                key={{kw}} 
                                className={{"sidebar-item " + (activeSection === kw ? 'active' : '')}}
                                href="#"
                                onClick={{(e) => {{e.preventDefault(); setActiveSection(kw)}}}}
                            >
                                <span className="icon">{{kw[0]}}</span>
                                {{kw}}
                            </a>
                        ))}}
                    </div>
                    
                    <div className="main">
                        <div className="stats">
                            {{appData.keywords.slice(0, 4).map(kw => (
                                <div key={{kw}} className="stat-card">
                                    <div className="number">{{Math.floor(Math.random() * 1000)}}</div>
                                    <div className="label">{{kw}}</div>
                                </div>
                            ))}}
                        </div>
                        
                        <div className="card">
                            <h2>{{activeSection}}</h2>
                            <p>这是「{{activeSection}}」功能模块的原型界面。在实际开发中，这里会实现完整的交互逻辑和数据展示。</p>
                            <table style={{{{marginTop: 16}}}}>
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>名称</th>
                                        <th>状态</th>
                                        <th>更新时间</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {{[1,2,3,4,5].map(i => (
                                        <tr key={{i}}>
                                            <td>{{i}}</td>
                                            <td>示例数据 {{i}}</td>
                                            <td><span style={{{{color: i%2===0 ? '#52c41a' : '#faad14'}}}}>{{i%2===0 ? '正常' : '待处理'}}</span></td>
                                            <td>2026-05-0{{i}}</td>
                                        </tr>
                                    ))}}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            );
        }}
        
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>"""

    @staticmethod
    def _generate_simple_prd(req_text: str) -> str:
        """生成简单的 PRD 文档（无 LLM 时的兜底方案）"""
        title = req_text.split("\n\n")[0] if "\n\n" in req_text else req_text[:50]
        
        # 根据需求文本分析功能模块
        features = []
        if "博客" in req_text or "blog" in req_text.lower():
            features = [
                {"name": "文章管理", "desc": "支持富文本编辑、草稿保存、定时发布、分类标签管理"},
                {"name": "评论系统", "desc": "多级评论、评论审核、@提及、表情回复"},
                {"name": "用户系统", "desc": "注册登录、个人主页、关注收藏、消息通知"},
                {"name": "内容展示", "desc": "响应式布局、SEO优化、文章推荐、热门排行"},
            ]
        elif "电商" in req_text or "商城" in req_text:
            features = [
                {"name": "商品管理", "desc": "商品分类、SKU管理、库存管理、价格策略"},
                {"name": "购物车", "desc": "加入购物车、数量修改、商品收藏、价格计算"},
                {"name": "订单系统", "desc": "订单创建、状态追踪、退款售后、物流查询"},
                {"name": "支付系统", "desc": "多渠道支付、订单支付、退款处理、账单管理"},
            ]
        elif "记账" in req_text or "财务" in req_text:
            features = [
                {"name": "收支记录", "desc": "手动记账、自动分类、多账户管理、批量导入"},
                {"name": "统计分析", "desc": "收支趋势、分类占比、月度报表、年度总结"},
                {"name": "预算管理", "desc": "预算设置、超支提醒、预算执行跟踪"},
                {"name": "数据导出", "desc": "Excel导出、PDF报表、数据备份、图表展示"},
            ]
        else:
            features = [
                {"name": "用户管理", "desc": "用户注册、登录认证、权限控制、个人信息管理"},
                {"name": "数据处理", "desc": "数据录入、数据校验、批量处理、数据导入导出"},
                {"name": "报表分析", "desc": "数据统计、图表展示、报表生成、趋势分析"},
                {"name": "系统设置", "desc": "参数配置、日志管理、系统监控、数据备份"},
            ]
        
        features_text = ""
        for i, f in enumerate(features):
            features_text += f"""
#### 2.1.{i+1} {f['name']}
**功能描述**：{f['desc']}

**用户故事**：
- 作为用户，我希望能够{f['name']}，以便更好地完成工作
- 系统应该提供直观的操作界面，降低学习成本

**验收标准**：
- 功能完整可用
- 响应时间 < 2秒
- 错误率 < 1%
"""
        
        return f"""# 产品需求文档 (PRD)

## 1. 产品概述

### 1.1 产品名称
{title}

### 1.2 产品定位
{req_text}

### 1.3 目标用户
- 主要用户群体：系统管理员、内容管理者、普通用户
- 用户特征：需要高效完成日常工作的专业人士
- 使用场景：办公环境、移动办公、数据管理

### 1.4 产品价值
- 提升工作效率，减少重复劳动
- 规范业务流程，降低操作错误
- 数据可视化，辅助决策分析

## 2. 功能需求

### 2.1 核心功能模块
{features_text}

### 2.2 用户界面要求
- 响应式设计，支持PC和移动端
- 符合WCAG 2.1 AA级无障碍标准
- 支持键盘快捷键操作
- 提供深色模式选项

### 2.3 数据要求
- 数据存储：支持MySQL/PostgreSQL
- 数据备份：每日自动备份，保留30天
- 数据恢复：支持7天内任意时间点恢复

## 3. 非功能需求

### 3.1 性能要求
- 页面加载时间：首屏 < 2秒
- API响应时间：P95 < 500ms
- 并发用户数：支持1000+在线用户
- 数据库查询：复杂查询 < 1秒

### 3.2 安全要求
- 用户认证：JWT Token + Refresh Token
- 数据传输：全站HTTPS加密
- 数据存储：敏感数据AES加密
- 访问控制：RBAC权限模型
- 日志审计：记录所有关键操作

### 3.3 可用性要求
- 系统可用率：99.9%
- 故障恢复时间：< 30分钟
- 数据一致性：最终一致性保证

### 3.4 兼容性要求
- 浏览器：Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- 操作系统：Windows 10+, macOS 11+, Linux
- 移动端：iOS 14+, Android 10+

## 4. 技术架构

### 4.1 技术栈
- 前端：React 18 + TypeScript + Ant Design
- 后端：Python FastAPI + SQLAlchemy
- 数据库：PostgreSQL 14+
- 缓存：Redis 6+
- 部署：Docker + Kubernetes

### 4.2 系统架构
```
用户层 -> 负载均衡 -> Web服务器 -> 应用服务器 -> 数据库
                    -> 缓存服务器
                    -> 文件存储
```

## 5. 项目规划

### 5.1 里程碑
- M1：核心功能开发（4周）
- M2：功能测试优化（2周）
- M3：上线试运行（2周）
- M4：正式发布（1周）

### 5.2 资源需求
- 前端开发：2人
- 后端开发：2人
- 测试工程师：1人
- 产品经理：1人

## 6. 风险评估

### 6.1 技术风险
- 数据量增长导致性能下降
- 第三方服务依赖风险

### 6.2 业务风险
- 用户需求变更频繁
- 市场竞争压力

### 6.3 风险应对
- 定期性能优化和扩容
- 敏捷开发，快速迭代
- 建立用户反馈机制

---
*文档版本：v1.0*
*最后更新：{datetime.now(timezone.utc).strftime('%Y-%m-%d')}*
"""

    @staticmethod
    def verifying_node(state: WorkflowState) -> dict:
        """校验节点 (GENERATED -> VERIFYING -> VERIFIED)

        对生成的原型和文档进行校验。
        """
        state.update_status(WorkflowStatus.VERIFYING)

        try:
            if state.pause_requested:
                state.update_status(WorkflowStatus.WAITING_USER_INPUT)
                return {"workflow_run": state.workflow_run}

            prototype_issues = []
            document_issues = []
            consistency_issues = []

            # 校验原型
            if state.prototype_html:
                html = state.prototype_html
                
                # 检查基本结构
                if '<!DOCTYPE html>' not in html:
                    prototype_issues.append({
                        "id": "P001",
                        "type": "structure",
                        "severity": "major",
                        "message": "HTML文档缺少DOCTYPE声明",
                        "suggestion": "添加 <!DOCTYPE html> 声明确保浏览器正确渲染",
                        "location": "HTML头部",
                    })
                
                if '<html' not in html:
                    prototype_issues.append({
                        "id": "P002",
                        "type": "structure",
                        "severity": "critical",
                        "message": "HTML文档缺少html标签",
                        "suggestion": "添加<html>标签包裹整个文档",
                        "location": "HTML结构",
                    })
                
                if '<head>' not in html:
                    prototype_issues.append({
                        "id": "P003",
                        "type": "structure",
                        "severity": "major",
                        "message": "HTML文档缺少head标签",
                        "suggestion": "添加<head>标签包含元数据和样式",
                        "location": "HTML结构",
                    })
                
                if '<meta charset' not in html:
                    prototype_issues.append({
                        "id": "P004",
                        "type": "accessibility",
                        "severity": "minor",
                        "message": "缺少字符编码声明",
                        "suggestion": "添加 <meta charset='UTF-8'> 确保正确显示中文",
                        "location": "head标签内",
                    })
                
                if '<meta name="viewport"' not in html:
                    prototype_issues.append({
                        "id": "P005",
                        "type": "responsiveness",
                        "severity": "minor",
                        "message": "缺少移动端视口设置",
                        "suggestion": "添加viewport meta标签支持响应式设计",
                        "location": "head标签内",
                    })
                
                # 检查无障碍性
                if '<button' in html and 'aria-label' not in html:
                    prototype_issues.append({
                        "id": "P006",
                        "type": "accessibility",
                        "severity": "minor",
                        "message": "按钮元素缺少无障碍标签",
                        "suggestion": "为按钮添加aria-label属性提高可访问性",
                        "location": "button元素",
                    })
                
                if '<input' in html and 'aria-label' not in html and '<label' not in html:
                    prototype_issues.append({
                        "id": "P007",
                        "type": "accessibility",
                        "severity": "minor",
                        "message": "输入框缺少标签关联",
                        "suggestion": "为input添加label或aria-label",
                        "location": "input元素",
                    })
                
                # 检查样式完整性
                if '<style>' not in html and 'style=' not in html:
                    prototype_issues.append({
                        "id": "P008",
                        "type": "styling",
                        "severity": "info",
                        "message": "未检测到内联样式或样式表",
                        "suggestion": "建议添加CSS样式提升视觉效果",
                        "location": "HTML文档",
                    })
                
                # 检查内容完整性
                if len(html) < 500:
                    prototype_issues.append({
                        "id": "P009",
                        "type": "completeness",
                        "severity": "info",
                        "message": "原型内容较少",
                        "suggestion": "可以添加更多交互元素和示例数据",
                        "location": "HTML文档",
                    })
            else:
                prototype_issues.append({
                    "id": "P010",
                    "type": "completeness",
                    "severity": "critical",
                    "message": "原型HTML内容为空",
                    "suggestion": "需要生成原型HTML内容",
                    "location": "工作流生成阶段",
                })

            # 校验文档
            if state.prd_document:
                prd = state.prd_document
                
                # 检查文档结构
                required_sections = ["产品概述", "功能需求", "非功能需求"]
                for section in required_sections:
                    if section not in prd:
                        document_issues.append({
                            "id": f"D{len(document_issues)+1:03d}",
                            "type": "completeness",
                            "severity": "major",
                            "message": f"文档缺少'{section}'章节",
                            "suggestion": f"添加'{section}'章节完善文档结构",
                            "location": "文档结构",
                        })
                
                # 检查内容丰富度
                if len(prd) < 1000:
                    document_issues.append({
                        "id": f"D{len(document_issues)+1:03d}",
                        "type": "completeness",
                        "severity": "info",
                        "message": "文档内容较少",
                        "suggestion": "可以补充更多详细的用户故事和验收标准",
                        "location": "文档内容",
                    })
                
                # 检查是否有用户故事
                if "用户故事" not in prd and "作为" not in prd:
                    document_issues.append({
                        "id": f"D{len(document_issues)+1:03d}",
                        "type": "methodology",
                        "severity": "minor",
                        "message": "文档缺少用户故事描述",
                        "suggestion": "添加用户故事帮助开发团队理解需求场景",
                        "location": "功能需求章节",
                    })
                
                # 检查是否有验收标准
                if "验收标准" not in prd:
                    document_issues.append({
                        "id": f"D{len(document_issues)+1:03d}",
                        "type": "testability",
                        "severity": "minor",
                        "message": "文档缺少验收标准",
                        "suggestion": "为每个功能添加明确的验收标准",
                        "location": "功能需求章节",
                    })
                
                # 检查技术架构
                if "技术架构" not in prd and "技术栈" not in prd:
                    document_issues.append({
                        "id": f"D{len(document_issues)+1:03d}",
                        "type": "technical",
                        "severity": "info",
                        "message": "文档缺少技术架构说明",
                        "suggestion": "添加技术栈和架构图帮助开发规划",
                        "location": "文档结构",
                    })
            else:
                document_issues.append({
                    "id": f"D{len(document_issues)+1:03d}",
                    "type": "completeness",
                    "severity": "critical",
                    "message": "PRD文档内容为空",
                    "suggestion": "需要生成PRD文档内容",
                    "location": "工作流生成阶段",
                })

            # 一致性检查
            if state.prototype_html and state.prd_document:
                # 检查标题一致性
                title_match = False
                if '<title>' in state.prototype_html:
                    title_start = state.prototype_html.find('<title>') + 7
                    title_end = state.prototype_html.find('</title>')
                    if title_end > title_start:
                        proto_title = state.prototype_html[title_start:title_end].strip()
                        if proto_title in state.prd_document:
                            title_match = True
                
                if not title_match:
                    consistency_issues.append({
                        "id": "C001",
                        "type": "consistency",
                        "severity": "info",
                        "message": "原型标题与PRD文档标题可能不一致",
                        "suggestion": "确保原型和文档使用相同的产品名称",
                        "location": "原型title标签 vs PRD标题",
                    })

            # 统计信息
            total_issues = len(prototype_issues) + len(document_issues) + len(consistency_issues)
            critical_count = sum(1 for i in prototype_issues + document_issues + consistency_issues if i.get("severity") == "critical")
            major_count = sum(1 for i in prototype_issues + document_issues + consistency_issues if i.get("severity") == "major")
            minor_count = sum(1 for i in prototype_issues + document_issues + consistency_issues if i.get("severity") == "minor")
            info_count = sum(1 for i in prototype_issues + document_issues + consistency_issues if i.get("severity") == "info")

            # 生成校验报告
            report = VerificationReport(
                report_id=f"report-{state.workflow_run.id}",
                created_at=datetime.now(timezone.utc),
                prototype_issues=prototype_issues,
                document_issues=document_issues,
                consistency_issues=consistency_issues,
                auto_fixed_issues=[],
                manual_review_required=[{
                    "id": "MR001",
                    "type": "review",
                    "severity": "info",
                    "message": f"共发现 {total_issues} 个问题（{critical_count}个严重，{major_count}个重要，{minor_count}个次要，{info_count}个建议）",
                    "suggestion": "请根据问题列表进行相应优化",
                    "location": "整体评估",
                }],
            )

            state.verification_report = report
            state.update_status(WorkflowStatus.VERIFIED)
            return {
                "workflow_run": state.workflow_run,
                "verification_report": report,
            }

        except Exception as e:
            state.error_message = str(e)
            state.update_status(WorkflowStatus.FAILED)
            return {"workflow_run": state.workflow_run, "error_message": state.error_message}

    @staticmethod
    def completing_node(state: WorkflowState) -> dict:
        """完成节点 (VERIFIED -> COMPLETED)

        标记工作流完成。
        """
        state.update_status(WorkflowStatus.COMPLETED)
        return {"workflow_run": state.workflow_run}

    @staticmethod
    def handle_user_input_node(state: WorkflowState) -> dict:
        """处理用户输入节点 (WAITING_USER_INPUT -> 恢复)

        处理用户的澄清回复。
        """
        if state.user_responses:
            # 用户已回复，清除等待状态
            state.update_status(WorkflowStatus.PARSING)
            return {"workflow_run": state.workflow_run, "user_responses": []}

        # 仍在等待用户输入
        state.update_status(WorkflowStatus.WAITING_USER_INPUT)
        return {"workflow_run": state.workflow_run}


def should_proceed_to_generate(state: WorkflowState) -> Literal["generate", "wait_for_user"]:
    """判断是否进入生成阶段

    如果解析阶段产生了澄清问题且用户尚未回复，等待用户输入。
    """
    if state.clarification_questions and not state.user_responses:
        return "wait_for_user"
    return "generate"


def should_proceed_to_complete(state: WorkflowState) -> Literal["complete", "failed"]:
    """判断是否进入完成阶段

    如果校验通过，进入完成阶段；否则标记失败。
    """
    if state.error_message:
        return "failed"
    if state.workflow_run.status == WorkflowStatus.VERIFIED:
        return "complete"
    return "failed"


def should_handle_generate_result(state: WorkflowState) -> Literal["verify", "failed", "pause"]:
    """判断生成节点执行结果

    如果有错误则失败结束；
    如果请求暂停则进入等待；
    否则继续进入校验。
    """
    if state.error_message:
        return "failed"
    if state.pause_requested:
        return "pause"
    return "verify"


def should_handle_pause(state: WorkflowState) -> Literal["pause", "continue"]:
    """判断是否需要暂停

    如果用户请求暂停，进入等待状态。
    """
    if state.pause_requested:
        return "pause"
    return "continue"


def build_workflow_graph(llm_handler=None) -> StateGraph:
    """构建工作流图

    定义完整的状态转换流程：
    INIT -> PARSING -> PARSED -> GENERATING -> GENERATED -> VERIFYING -> VERIFIED -> COMPLETED

    异常路径：
    - 任何阶段 -> FAILED
    - PARSING -> WAITING_USER_INPUT -> PARSING（循环）
    """
    workflow = StateGraph(WorkflowState)

    # 添加节点
    workflow.add_node("parse", lambda state: WorkflowNodes.parsing_node(state, llm_handler))
    workflow.add_node("generate", lambda state: WorkflowNodes.generating_node(state, llm_handler))
    workflow.add_node("verify", WorkflowNodes.verifying_node)
    workflow.add_node("complete", WorkflowNodes.completing_node)
    workflow.add_node("handle_user_input", WorkflowNodes.handle_user_input_node)

    # 定义边
    workflow.add_edge(START, "parse")

    # PARSING 后的条件路由
    workflow.add_conditional_edges(
        "parse",
        should_proceed_to_generate,
        {
            "generate": "generate",
            "wait_for_user": "handle_user_input",
        },
    )

    # 用户输入处理后的路由
    workflow.add_edge("handle_user_input", "parse")

    # GENERATING -> GENERATED 后进入 VERIFYING
    workflow.add_conditional_edges(
        "generate",
        should_handle_generate_result,
        {
            "verify": "verify",
            "pause": "handle_user_input",
            "failed": END,
        },
    )

    # VERIFYING 后的条件路由
    workflow.add_conditional_edges(
        "verify",
        should_proceed_to_complete,
        {
            "complete": "complete",
            "failed": END,
        },
    )

    # 完成后结束
    workflow.add_edge("complete", END)

    return workflow


def create_workflow_app(llm_handler=None) -> object:
    """创建并编译工作流应用

    Args:
        llm_handler: LLM 处理器实例，用于需求解析等 AI 驱动节点

    Returns:
        编译后的 LangGraph 应用
    """
    graph = build_workflow_graph(llm_handler=llm_handler)
    return graph.compile()
