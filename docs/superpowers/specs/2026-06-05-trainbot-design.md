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
trainbot --test         # 测试配置（增强版）

# 通知
trainbot --notify       # 手动发一次通知
trainbot --notify-all   # 发送所有训练状态

# 监控（后台运行）
trainbot --daemon       # 启动后台监控
trainbot --stop         # 停止后台监控
trainbot --stop-all     # 停止所有监控
trainbot --status       # 查看后台监控状态

# 通知历史
trainbot --history      # 查看最近10条通知
trainbot --history --all    # 查看全部
trainbot --history --clear  # 清空历史

# 更新与维护
trainbot --check-update # 检查更新
trainbot --update       # 更新到最新版本
trainbot --uninstall    # 卸载

# 配置迁移
trainbot --export       # 导出配置
trainbot --import FILE  # 导入配置

# 日志
trainbot --log          # 查看trainbot日志
trainbot --log --tail N # 查看最后N行
trainbot --log --clear  # 清空日志

# 批量操作
trainbot --set-webhook URL  # 设置webhook
trainbot --set-alert BOOL   # 开启/关闭异常检测
trainbot --set-interval N   # 设置定时汇报间隔
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
    "check_nan": true,
    "stuck_minutes": 30,
    "check_oom": true,
    "check_crash": true
  },
  "monitor": {
    "mode": "auto",
    "log_dir": null,
    "custom_patterns": null,
    "tensorboard_dir": null,
    "proc_root": "/proc"
  },
  "webhooks": {
    "default": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
    "alerts": null,
    "reports": null
  },
  "notify_rules": {
    "complete": "default",
    "alert": "default",
    "report": "default"
  },
  "auto_check_update": true,
  "update_channel": "stable"
}
```

**配置说明：**
- `monitor.mode`: 监控模式
  - `auto`: 自动发现（默认）
  - `log_dir`: 监控指定目录
  - `tensorboard`: 读取TensorBoard日志
  - `custom`: 使用自定义正则
- `monitor.log_dir`: 日志目录路径（mode=log_dir时必填）
- `monitor.custom_patterns`: 自定义正则表达式（mode=custom时必填）
- `monitor.tensorboard_dir`: TensorBoard日志目录（mode=tensorboard时必填）

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

### 3.4 监控方式

**支持多种数据源：**

| 数据源 | 描述 | 优先级 |
|--------|------|--------|
| stdout日志 | 从/proc/pid/fd/1读取进程输出 | P0 |
| 日志文件 | 监控指定目录的日志文件 | P0 |
| TensorBoard | 读取events.out.tfevents文件 | P1 |
| wandb | 通过wandb API获取运行状态 | P1 |
| 自定义正则 | 用户配置正则表达式匹配 | P1 |

**支持的日志格式（内置）：**

```python
# 格式1: PyTorch Lightning / 自定义
r'Epoch\s+(\d+)/(\d+).*?Val\s+[\d.]+\s+([\d.]+)\s+([\d.]+)'

# 格式2: HuggingFace Trainer
r'Epoch\s+(\d+).*?loss[:\s]+([\d.]+).*?accuracy[:\s]+([\d.]+)'

# 格式3: 融合实验格式
r'Ep\s+(\d+).*?Val Loss\s+[\d.]+\s+Acc\s+([\d.]+).*?MF1\s+([\d.]+)'

# 格式4: 简单loss格式
r'Epoch\s+(\d+)/(\d+).*?loss[:\s]+([\d.]+)'

# 格式5: Keras格式
r'Epoch\s+(\d+)/(\d+).*?val_accuracy[:\s]+([\d.]+)'

# 格式6: 自定义print格式
r'\[(\d+)/(\d+)\].*?val_loss[:\s]+([\d.]+).*?val_acc[:\s]+([\d.]+)'
```

**自定义正则配置：**
```json
{
  "custom_patterns": {
    "epoch": "Epoch\\s+(\\d+)/(\\d+)",
    "loss": "loss[:\\s]+([\\d.]+)",
    "acc": "accuracy[:\\s]+([\\d.]+)",
    "mf1": "MF1[:\\s]+([\\d.]+)"
  }
}
```

**TensorBoard支持：**
```python
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

ea = EventAccumulator(log_dir)
ea.Reload()
# 获取最新scalar
loss = ea.Scalars('loss')[-1].value
acc = ea.Scalars('accuracy')[-1].value
```

### 3.5 异常检测算法

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
# ? 选择监控模式:
#   1. 自动发现（默认，推荐）
#   2. 监控指定目录
#   3. 读取TensorBoard日志
#   4. 自定义正则表达式
# > 1
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
├── CHANGELOG.md          # 更新日志
├── LICENSE               # MIT协议
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-06-05-trainbot-design.md  # 本文档
├── examples/
│   ├── config_example.json    # 配置示例
│   └── custom_patterns.json   # 自定义正则示例
└── screenshots/
    ├── tm_output.png          # tm命令截图
    ├── setup_wizard.png       # 配置向导截图
    └── dingtalk_notify.png    # 钉钉通知截图
```

### README.md 结构

```markdown
# trainbot

一句话描述 + 徽章（stars、license、python版本）

## 功能亮点
- ✓ 无需改代码，自动发现训练
- ✓ 训练完成/异常时钉钉通知
- ✓ 支持多种日志格式
- ✓ 支持自定义正则表达式
- ✓ 零依赖，单文件

## 截图展示
![tm命令输出](screenshots/tm_output.png)
![钉钉通知](screenshots/dingtalk_notify.png)

## 快速开始
1. 下载
2. 配置
3. 使用

## 详细功能
- 监控模式
- 通知格式
- 异常检测
- 自定义配置

## 配置说明
- webhook获取
- 配置文件格式
- 环境变量

## 常见问题（FAQ）
- Q: 如何获取钉钉webhook？
- Q: 支持哪些日志格式？
- Q: 如何自定义正则？
- Q: 多个训练同时运行怎么办？

## 贡献指南
- 如何提交issue
- 如何贡献代码
- 开发环境搭建

## License
MIT
```

## 6. 发布计划

**v0.1 (MVP):**
- 保留原有tm功能
- 添加`--setup`交互式配置
- 添加`--notify`手动通知
- 添加训练完成自动通知
- 添加异常检测（loss/acc/NaN）
- 支持多种日志格式（6种内置格式）
- 支持自定义正则表达式
- 支持监控指定目录
- 支持TensorBoard日志读取

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
| 多日志格式 | ✓ | ✗ | ✗ | ✗ |
| 自定义正则 | ✓ | ✗ | ✗ | ✗ |
| TensorBoard支持 | ✓ | ✗ | ✓ | ✓ |
| 免费 | ✓ | ✓ | ✓ | ✓ |
| 本地运行 | ✓ | ✗ | ✓ | ✓ |

**差异化优势：** trainbot是唯一一个"无需改代码+多格式支持+钉钉通知"的训练监控工具。

## 8. 边界情况处理

### 8.1 多训练进程

**场景：** 同时运行多个训练（如不同GPU上的不同实验）

**处理方式：**
- 按GPU编号+实验名区分不同训练
- 每个训练独立追踪状态
- 通知时合并显示所有训练状态

**通知示例：**
```
══════════════════════════════
训练状态汇报
══════════════════════════════
GPU 0: resnet18    Epoch 45/50  Acc 92.3%
GPU 1: resnet50    Epoch 32/50  Acc 89.1%
GPU 2: distill     Epoch 28/50  loss 0.023
GPU 3: fusion      Epoch 15/50  Acc 85.6%
```

### 8.2 训练重启

**场景：** 训练中断后重启，避免重复通知

**处理方式：**
- 记录已通知的进程PID到`~/.trainbot/notified.json`
- 同一PID只通知一次
- 新PID视为新训练，重新追踪

**配置：**
```json
// ~/.trainbot/notified.json
{
  "notified_pids": [12345, 12346],
  "last_update": "2026-06-05T10:30:00"
}
```

### 8.3 日志文件轮转

**场景：** 日志文件被logrotate轮转，inode变化

**处理方式：**
- 监控文件路径而非inode
- 检测到文件大小减小时，重新读取
- 保留最近100行历史用于趋势分析

### 8.4 网络重试

**场景：** 钉钉API调用失败（网络抖动、限流等）

**处理方式：**
- 失败后指数退避重试：1s → 2s → 4s → 8s
- 最多重试3次
- 重试失败后记录到日志，不阻塞监控

### 8.5 日志编码

**场景：** 不同系统日志编码不同（UTF-8、Latin-1等）

**处理方式：**
- 优先尝试UTF-8解码
- 失败后尝试Latin-1
- 最后使用errors='ignore'

### 8.6 训练失败检测

**场景：** 训练进程崩溃、OOM（GPU内存不足）

**检测方式：**
```python
# 进程崩溃检测
if pid not in running_pids:
    notify("训练进程异常退出", pid)

# OOM检测（通过nvidia-smi）
if "CUDA out of memory" in log_tail:
    notify("GPU内存不足(OOM)", pid)

# dmesg检测OOM killer
if "Out of memory" in subprocess.run(["dmesg"]).stdout:
    notify("系统OOM Killer终止了训练", pid)
```

**通知示例：**
```
══════════════════════════════
⚠️ 训练异常告警
══════════════════════════════
实验: resnet18
GPU: cuda:0
状态: 进程异常退出
最后Epoch: 32/50
最后Val Acc: 85.3%
退出码: 137 (OOM Killer)
```

### 8.7 训练卡住检测

**场景：** 训练长时间没有新输出（死循环、挂起）

**检测方式：**
```python
# 记录最后输出时间
last_output_time = get_last_log_time(log_path)

# 超过阈值没有新输出
if time.time() - last_output_time > stuck_threshold:
    notify("训练疑似卡住", pid)
```

**配置：**
```json
{
  "alert_thresholds": {
    "stuck_minutes": 30  // 30分钟没有新输出视为卡住
  }
}
```

### 8.8 多Webhook支持

**场景：** 不同通知发到不同钉钉群

**配置：**
```json
{
  "webhooks": {
    "default": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
    "alerts": "https://oapi.dingtalk.com/robot/send?access_token=yyy",
    "reports": "https://oapi.dingtalk.com/robot/send?access_token=zzz"
  },
  "notify_rules": {
    "complete": "default",
    "alert": "alerts",
    "report": "reports"
  }
}
```

**简化配置（向后兼容）：**
```json
{
  "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"
}
// 等同于
{
  "webhooks": {"default": "..."},
  "notify_rules": {"complete": "default", "alert": "default", "report": "default"}
}
```

### 8.9 通知历史

**场景：** 查看历史通知记录

**存储位置：** `~/.trainbot/history.json`

**记录格式：**
```json
{
  "notifications": [
    {
      "time": "2026-06-05T10:30:00",
      "type": "complete",
      "experiment": "resnet18",
      "gpu": "cuda:0",
      "epoch": "50/50",
      "val_acc": "92.3%",
      "webhook": "default"
    }
  ]
}
```

**查看命令：**
```bash
trainbot --history          # 查看最近10条
trainbot --history --all    # 查看全部
trainbot --history --clear  # 清空历史
```

## 9. 兼容性

### 9.1 Python版本

- **最低要求：** Python 3.8+
- **推荐版本：** Python 3.10+
- **不支持：** Python 2.x

**原因：**
- 使用f-string（3.6+）
- 使用walrus operator（3.8+）
- 使用type hints（3.5+）

### 9.2 操作系统

| 系统 | 支持程度 | 说明 |
|------|----------|------|
| Linux | ✓ 完全支持 | 主要开发平台 |
| macOS | ⚠️ 有限支持 | /proc不可用，需适配 |
| Windows | ✗ 不支持 | 无/proc，需重写 |

**Linux发行版测试：**
- Ubuntu 20.04/22.04
- CentOS 7/8
- Debian 10/11

### 9.3 依赖

**零依赖设计：**
- 只使用Python标准库
- 不需要pip install任何包
- 不需要额外系统工具

**可选依赖（增强功能）：**
- `tensorboard`: TensorBoard日志支持
- `requests`: HTTP请求（标准库urllib也可）

## 10. 错误处理

### 10.1 配置错误

| 错误 | 提示信息 | 解决方案 |
|------|----------|----------|
| 未配置webhook | "请先运行 trainbot --setup 配置钉钉webhook" | 引导配置 |
| webhook格式错误 | "webhook URL格式不正确，请检查" | 提示正确格式 |
| webhook无效 | "webhook连接失败，请检查URL是否正确" | 提示测试命令 |

### 10.2 权限错误

| 错误 | 提示信息 | 解决方案 |
|------|----------|----------|
| /proc不可读 | "无法读取进程信息，请检查权限" | 提示sudo或检查SELinux |
| 日志文件不可读 | "无法读取日志文件: {path}" | 提示chmod或检查路径 |
| 配置目录不可写 | "无法写入配置目录: ~/.trainbot/" | 提示创建目录 |

### 10.3 运行时错误

| 错误 | 提示信息 | 解决方案 |
|------|----------|----------|
| 网络超时 | "钉钉API超时，正在重试 ({n}/3)" | 自动重试 |
| API限流 | "钉钉API限流，等待{seconds}秒后重试" | 自动等待 |
| 日志解析失败 | "无法解析日志格式，跳过该训练" | 记录到日志 |
| 进程消失 | "训练进程 {pid} 已结束" | 清理状态 |

### 10.4 用户友好提示

**首次运行引导：**
```bash
$ trainbot
╔══════════════════════════════════════════════════════════════╗
║                    欢迎使用 trainbot!                        ║
╠══════════════════════════════════════════════════════════════╣
║  首次使用需要配置钉钉webhook                                 ║
║  请运行: trainbot --setup                                    ║
║                                                              ║
║  获取webhook:                                                ║
║  1. 打开钉钉群 → 群设置 → 智能群助手                         ║
║  2. 添加机器人 → 自定义                                      ║
║  3. 复制webhook URL                                          ║
╚══════════════════════════════════════════════════════════════╝
```

**配置验证（增强版）：**
```bash
$ trainbot --test
╔══════════════════════════════════════════════════════════════╗
║                    配置验证报告                              ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ 配置文件存在: ~/.trainbot/config.json                     ║
║  ✓ 配置格式正确                                              ║
║  ✓ webhook格式正确                                           ║
║  ✓ webhook连接成功                                           ║
║  ✓ 发送测试消息成功                                          ║
║  ✓ 通知历史可写                                              ║
║  ✓ 监控模式: auto                                            ║
║  ✓ 异常检测: 已开启                                          ║
║  ✓ 定时汇报: 已关闭                                          ║
╠══════════════════════════════════════════════════════════════╣
║  测试消息已发送到钉钉群，请检查是否收到。                    ║
╚══════════════════════════════════════════════════════════════╝
```

## 11. 更新与维护

### 11.1 更新机制

**检查更新：**
```bash
trainbot --check-update
# 当前版本: v0.1.0
# 最新版本: v0.2.0
# 运行 trainbot --update 进行更新
```

**自动更新：**
```bash
trainbot --update
# 下载最新版本...
# 备份当前版本: ~/.trainbot/backup/trainbot_v0.1.0
# 更新完成！
```

**更新配置（可选）：**
```json
{
  "auto_check_update": true,  // 自动检查更新
  "update_channel": "stable"  // stable/beta
}
```

### 11.2 卸载机制

**完全卸载：**
```bash
trainbot --uninstall
# 确认卸载 trainbot? (y/n): y
# 停止后台监控...
# 删除程序文件: ~/.local/bin/trainbot
# 删除配置目录: ~/.trainbot/ (可选)
# 卸载完成！

# 保留配置（用于重装）
trainbot --uninstall --keep-config
```

**手动卸载：**
```bash
# 1. 停止后台监控
trainbot --stop

# 2. 删除程序文件
rm ~/.local/bin/trainbot

# 3. 删除配置（可选）
rm -rf ~/.trainbot/

# 4. 删除别名（如果添加了）
# 编辑 ~/.bashrc，删除 alias tm="trainbot"
```

### 11.3 配置迁移

**导出配置：**
```bash
trainbot --export > trainbot_config.json
# 或指定路径
trainbot --export --output /path/to/config.json
```

**导入配置：**
```bash
trainbot --import trainbot_config.json
# 配置已导入！
```

**迁移步骤：**
```bash
# 在旧机器
trainbot --export > trainbot_config.json

# 复制到新机器
scp trainbot_config.json new_machine:~/

# 在新机器
wget https://raw.githubusercontent.com/MSWEIMZ/trainbot/main/trainbot -O ~/.local/bin/trainbot
chmod +x ~/.local/bin/trainbot
trainbot --import ~/trainbot_config.json
trainbot --test
```

### 11.4 日志查看

**trainbot自身日志：**
```bash
trainbot --log              # 查看最近日志
trainbot --log --tail 100   # 查看最后100行
trainbot --log --clear      # 清空日志
```

**日志位置：** `~/.trainbot/trainbot.log`

**日志格式：**
```
[2026-06-05 10:30:00] INFO: 发现训练进程 PID=12345 GPU=cuda:0
[2026-06-05 10:30:01] INFO: 解析日志成功 Epoch=32/50 Acc=85.3%
[2026-06-05 10:31:00] INFO: 发送通知成功 type=report
[2026-06-05 10:35:00] WARN: 训练进程 PID=12345 超过30分钟无输出
[2026-06-05 10:36:00] ERROR: webhook调用失败，重试中 (1/3)
```

## 12. 环境支持

### 12.1 Python虚拟环境

**检测方式：**
```python
# 检测当前Python环境
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    env_type = "virtualenv"
elif 'CONDA_DEFAULT_ENV' in os.environ:
    env_type = "conda"
else:
    env_type = "system"
```

**使用建议：**
```bash
# 推荐：使用系统Python
/usr/bin/python3 ~/.local/bin/trainbot

# 或在虚拟环境中安装
pip install trainbot  # 未来支持
```

### 12.2 Conda环境

**配置方式：**
```bash
# 方式1：使用当前conda环境
conda activate myenv
trainbot --setup

# 方式2：指定conda环境
trainbot --setup --python /path/to/conda/envs/myenv/bin/python
```

**注意事项：**
- trainbot会自动检测当前环境
- 如果conda环境没有Python，会提示错误
- 建议在base环境中安装trainbot

### 12.3 Docker容器

**场景：** 训练在Docker容器中运行

**支持方式：**
```bash
# 方式1：在容器内运行trainbot
docker exec -it my_container trainbot --setup

# 方式2：从宿主机监控容器（需要挂载/proc）
docker run -v /proc:/host/proc:ro my_train_image
trainbot --setup --proc-root /host/proc
```

**配置：**
```json
{
  "monitor": {
    "proc_root": "/proc",  // 或 "/host/proc" 用于Docker
    "container_mode": false
  }
}
```

### 12.4 远程服务器

**场景：** 训练在远程服务器上运行

**支持方式：**
```bash
# 方式1：SSH隧道
ssh -L 8080:localhost:8080 remote_server
trainbot --web http://localhost:8080

# 方式2：远程执行
ssh remote_server "trainbot --notify"

# 方式3：共享配置
scp ~/.trainbot/config.json remote_server:~/.trainbot/
```

## 13. 批量操作

### 13.1 批量停止

**停止所有监控：**
```bash
trainbot --stop-all
# 停止 trainbot daemon (PID: 12345)
# 停止 trainbot daemon (PID: 12346)
# 已停止 2 个监控进程
```

### 13.2 批量通知

**手动发送所有状态：**
```bash
trainbot --notify-all
# 发送 cuda:0 状态...
# 发送 cuda:1 状态...
# 发送 cuda:2 状态...
# 已发送 3 条通知
```

### 13.3 批量配置

**批量修改配置：**
```bash
# 修改所有webhook
trainbot --set-webhook https://new-webhook-url

# 开启所有异常检测
trainbot --set-alert true

# 设置定时汇报
trainbot --set-interval 2
```

## 14. 风险与挑战

## 11. 风险与挑战

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
