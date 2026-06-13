# Agent 自我进化功能使用指南

## 功能概述

自我进化功能使 Agent 能够从历史任务中学习、分析成功/失败模式、自动优化策略、积累最佳实践，持续提升任务执行质量和效率。

## 核心组件

```
自我进化系统
├── 经验收集器 (Experience Collector) - 从任务执行中收集经验数据
├── 知识提炼器 (Knowledge Distiller) - 从经验中提取可复用的知识
├── 策略优化器 (Strategy Optimizer) - 应用优化规则改进 Agent 表现
└── 进化管理器 (Evolution Manager) - 统筹整个进化流程
```

## API 接口

所有接口都需要认证，通过 `/api/v1/` 前缀访问。

### 1. 获取进化状态

```bash
GET /api/v1/evolution/status
```

返回当前进化系统的状态、指标和配置。

### 2. 触发进化流程

```bash
POST /api/v1/evolution/trigger
Content-Type: application/json

{
  "force": false
}
```

手动触发进化分析流程。

### 3. 获取进化指标

```bash
GET /api/v1/evolution/metrics
```

获取详细的进化指标，包括：
- 总经验数
- 质量分布（优秀/良好/一般/较差）
- 成功率
- 平均执行时间
- 用户满意度
- 性能提升率

### 4. 获取优化建议

```bash
GET /api/v1/evolution/suggestions?task_type=requirement_analysis
```

获取针对特定任务类型的优化建议。

### 5. 查询经验记录

```bash
GET /api/v1/evolution/experiences?limit=50&quality=excellent&success=true
```

参数：
- `limit`: 数量限制（默认 50）
- `task_type`: 任务类型过滤
- `quality`: 质量等级（excellent/good/average/poor）
- `success`: 成功/失败过滤

### 6. 获取经验详情

```bash
GET /api/v1/evolution/experiences/{experience_id}
```

### 7. 提交用户反馈

```bash
POST /api/v1/evolution/experiences/{experience_id}/feedback
Content-Type: application/json

{
  "feedback": "非常好，原型和文档都很完整",
  "satisfaction": 5
}
```

### 8. 回滚优化

```bash
POST /api/v1/evolution/rollback/{rule_id}
```

### 9. 导出进化数据

```bash
GET /api/v1/evolution/export
```

导出完整的进化数据用于分析或备份。

## 使用示例

### Python SDK

```python
from pm_workstation.agents.evolution import AgentEvolutionManager

# 创建管理器
manager = AgentEvolutionManager(storage_dir="./data/evolution")

# 收集经验（自动在工作流完成后调用）
manager.collect_experience(state)

# 获取进化指标
metrics = manager.get_evolution_metrics()
print(f"总经验数：{metrics.total_experiences}")
print(f"成功率：{metrics.overall_success_rate * 100:.1f}%")
print(f"性能提升：{metrics.performance_improvement_rate:.1f}%")

# 手动触发进化
result = manager.trigger_evolution()
if result["status"] == "completed":
    print(f"应用了 {len(result['optimizations'])} 个优化")

# 获取优化建议
suggestions = manager.get_optimization_suggestions(task_type="prototype_generation")
for sug in suggestions:
    print(f"建议：{sug['description']}")
```

### cURL 示例

```bash
# 获取状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/evolution/status

# 触发进化
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": false}' \
  http://localhost:8000/api/v1/evolution/trigger

# 获取优化建议
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/evolution/suggestions?task_type=document_generation"
```

## 配置选项

```python
from pm_workstation.agents.evolution import AgentEvolutionConfig

config = AgentEvolutionConfig(
    enabled=True,                      # 是否启用自我进化
    auto_apply_optimizations=False,    # 是否自动应用优化
    min_confidence_threshold=0.7,      # 最小置信度阈值
    collect_experiences=True,          # 收集经验
    min_quality_for_learning="good",   # 学习最低质量
    analysis_interval_hours=24,        # 分析间隔 (小时)
    min_experiences_for_analysis=10,   # 分析所需最少经验数
    max_optimizations_per_cycle=5,     # 每周期最大优化数
    enable_rollback=True,              # 启用回滚
    rollback_on_failure=True,          # 失败时回滚
)

manager = AgentEvolutionManager(config=config)
```

## 经验质量评级

系统会自动评估经验质量：

- **Excellent (优秀)**: 完整的产出物 + 正面用户反馈
- **Good (良好)**: 有部分产出物，任务成功完成
- **Average (一般)**: 普通案例，无特别亮点
- **Poor (较差)**: 失败案例或有问题

## 优化规则类型

系统会自动生成以下类型的优化规则：

1. **Token 用量优化**: 当 Token 用量过高时简化 prompt
2. **执行时间优化**: 当执行时间过长时启用并行执行
3. **技能精简**: 限制使用的技能数量，聚焦核心技能

## 数据持久化

所有进化数据保存在 `./data/evolution/` 目录：

```
data/evolution/
├── experiences/      # 经验记录 (JSON 文件)
├── knowledge/        # 提炼的知识
│   ├── success_patterns.json
│   ├── optimization_rules.json
│   └── best_practices.json
└── evolution_history.json
```

## 最佳实践

1. **定期触发进化**: 建议每 24 小时或积累 10+ 个经验后触发一次
2. **收集用户反馈**: 用户反馈是评估质量的重要指标
3. **审慎自动应用**: 建议手动审查优化规则后再应用
4. **导出备份**: 定期导出进化数据，防止丢失
5. **监控指标趋势**: 关注成功率和执行时间的变化趋势

## 故障排除

### 经验收集中断

检查 `./data/evolution/experiences/` 目录是否有写入权限。

### 进化分析失败

确保至少有 5 个经验记录才能触发分析。

### 优化规则未生效

检查规则是否在启用状态，置信度是否达到阈值。

## 扩展开发

### 自定义优化规则

```python
from pm_workstation.agents.evolution.evolution_models import OptimizationRule

custom_rule = OptimizationRule(
    id="custom_001",
    name="自定义优化",
    description="针对特定场景的优化",
    trigger_conditions={"task_type": "market_research"},
    action_type="parameter_tune",
    action_params={"max_tokens": 8192},
    enabled=True,
    confidence=0.8,
)

manager.optimizer._rules[custom_rule.id] = custom_rule
```

### 自定义质量评估

继承 `ExperienceCollector` 并重写 `_evaluate_quality` 方法。

## 版本历史

- **v1.0** (2026-06): 初始版本
  - 基础经验收集
  - 知识提炼
  - 策略优化
  - REST API
