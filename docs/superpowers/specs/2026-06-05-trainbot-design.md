# Trainbot 设计规格

## 1. 概述

**项目名称：** trainbot

**一句话描述：** 无需改代码的GPU训练监控+钉钉告警工具

**目标用户：** 深度学习研究者、ML工程师

**解决的问题：**
- 训练跑几天，没人盯着，出问题白跑
- nvidia-smi只显示GPU占用，不知道训练状态
- wandb/tensorboard需要改代码接入

**核心卖点：** 不用改代码，自动发现训练进程，完成/异常时钉钉通知

## 2. 功能规格

### 2.1 核心功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 训练监控 | 自动发现GPU训练进程，显示epoch/loss/acc | P0 |
| 训练完成通知 | 训练结束时发钉钉通知 | P0 |
| 异常检测 | loss飙升、acc骤降、NaN时告警 | P0 |
| 交互式配置 | `trainbot --setup` 一次配置 | P0 |
| 定时汇报 | 可选，每N小时发一次状态 | P1 |
| 手动通知 | `trainbot --notify` 手动发一次 | P1 |

### 2.2 命令行接口

```bash
# 查看状态（保留原有tm命令）
tm
trainbot                # 同tm

# 配置
trainbot --setup        # 交互式配置
trainbot --config       # 查看当前配置

# 通知
trainbot --notify       # 手动发一次通知
trainbot --test         # 测试webhook连接

# 监控（后台运行）
trainbot --daemon       # 启动后台监控
trainbot --stop         # 停止后台监控
trainbot --status       # 查看后台监控状态
```

### 2.3 通知触发条件

| 条件 | 描述 | 默认 |
|------|------|------|
| 训练完成 | epoch达到总数，或训练进程结束 | 开启 |
| 异常检测 | loss突然飙升(>2x)、acc骤降(>20%)、出现NaN | 开启 |
| 定时汇报 | 每N小时发一次当前状态 | 关闭 |

### 2.4 通知格式

**简洁版：**
```
══════════════════════════════
训练完成通知
══════════════════════════════
实验: resnet18
GPU: cuda:0
Epoch: 50/50
Val Acc: 92.3%
Val MF1: 89.1%
耗时: 4h32m
```

**详细版：**
```
══════════════════════════════
训练完成通知
══════════════════════════════
实验: resnet18 (ImageNet预训练)
GPU: cuda:0
Epoch: 50/50
Val Acc: 92.3% (best: 93.1% @ep45)
Val MF1: 89.1%
趋势: ████████████████░░ 95%
耗时: 4h32m
损失: 0.023
```

## 3. 技术设计

### 3.1 架构

```
trainbot/
├── trainbot              # 主脚本（单文件，用户下载这一个）
├── config.json           # 用户配置（~/.trainbot/config.json）
└── README.md             # 说明文档
```

**设计原则：**
- 单文件发布：用户只下载一个Python文件
- 零依赖：只用Python标准库
- 向后兼容：保留原有`tm`功能

### 3.2 配置文件

**位置：** `~/.trainbot/config.json`

**内容：**
```json
{
  "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  "format": "detailed",
  "alert": true,
  "interval_hours": 0,
  "alert_thresholds": {
    "loss_spike": 2.0,
    "acc_drop": 0.2,
    "check_nan": true
  }
}
```

### 3.3 钉钉机器人API

**请求格式：**
```python
import requests
import json

webhook = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
data = {
    "msgtype": "text",
    "text": {
        "content": message
    }
}
requests.post(webhook, json=data)
```

### 3.4 异常检测算法

**Loss飙升检测：**
```python
# 当前loss > 最近10个epoch平均loss * 2
if current_loss > avg_loss * 2:
    alert("Loss spike detected")
```

**Acc骤降检测：**
```python
# 当前acc < 最近10个epoch平均acc * 0.8
if current_acc < avg_acc * 0.8:
    alert("Accuracy drop detected")
```

**NaN检测：**
```python
if math.isnan(loss) or math.isnan(acc):
    alert("NaN detected")
```

### 3.5 后台监控

**实现方式：** 使用`nohup`或Python的`daemon`模式

**监控循环：**
```python
while True:
    # 1. 获取所有训练进程
    processes = get_gpu_processes()

    # 2. 解析每个进程的日志
    for p in processes:
        info = parse_log(p['log_path'])

        # 3. 检测异常
        if check_alert(info):
            send_notification(info, "alert")

        # 4. 检测完成
        if check_complete(info):
            send_notification(info, "complete")

    # 5. 定时汇报
    if interval > 0 and time_to_report():
        send_status_report(processes)

    # 6. 等待
    sleep(60)  # 每分钟检查一次
```

## 4. 用户流程

### 4.1 首次安装

```bash
# 1. 下载
wget https://raw.githubusercontent.com/MSWEIMZ/trainbot/main/trainbot -O ~/.local/bin/trainbot
chmod +x ~/.local/bin/trainbot

# 2. 配置
trainbot --setup
# ? 请输入钉钉机器人webhook URL: https://oapi.dingtalk.com/robot/send?access_token=xxx
# ? 选择通知格式 (1-简洁 2-详细): 2
# ? 是否开启异常检测 (y/n): y
# ? 定时汇报间隔 (小时，0为关闭): 0
# ✓ 配置已保存到 ~/.trainbot/config.json

# 3. 测试
trainbot --test
# ✓ Webhook连接成功！
```

### 4.2 日常使用

```bash
# 查看当前训练状态
tm

# 启动后台监控（自动通知）
trainbot --daemon

# 手动发一次通知
trainbot --notify

# 停止后台监控
trainbot --stop
```

## 5. 项目结构

```
train-monitor/
├── trainbot              # 主脚本（单文件）
├── README.md             # 说明文档
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-06-05-trainbot-design.md  # 本文档
└── examples/
    └── config_example.json  # 配置示例
```

## 6. 发布计划

**v0.1 (MVP):**
- 保留原有tm功能
- 添加`--setup`交互式配置
- 添加`--notify`手动通知
- 添加训练完成自动通知
- 添加异常检测（loss/acc/NaN）

**v0.2:**
- 添加`--daemon`后台监控
- 添加定时汇报
- 添加通知历史记录

**v0.3:**
- 添加更多通知渠道（邮件、Telegram）
- 添加web界面（可选）

## 7. 竞品对比

| 功能 | trainbot | wandb | tensorboard | mlflow |
|------|----------|-------|-------------|--------|
| 无需改代码 | ✓ | ✗ | ✗ | ✗ |
| 轻量级CLI | ✓ | ✗ | ✗ | ✗ |
| 钉钉通知 | ✓ | ✗ | ✗ | ✗ |
| 异常检测 | ✓ | ✓ | ✗ | ✓ |
| 免费 | ✓ | ✓ | ✓ | ✓ |
| 本地运行 | ✓ | ✗ | ✓ | ✓ |

**差异化优势：** trainbot是唯一一个"无需改代码+钉钉通知"的训练监控工具。

## 8. 风险与挑战

| 风险 | 应对策略 |
|------|----------|
| 日志格式不统一 | 支持多种格式，用户可自定义正则 |
| 钉钉API变更 | 封装API调用，便于更新 |
| 用户不配置 | 提供合理的默认值，首次运行引导 |
| 多用户冲突 | 按用户隔离配置和进程 |

## 9. 成功指标

**短期（1个月）：**
- GitHub stars: 100+
- 用户反馈: 收到10+个issue

**中期（3个月）：**
- GitHub stars: 500+
- 贡献者: 3+人

**长期（6个月）：**
- GitHub stars: 1000+
- 被其他项目引用
