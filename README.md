# trainbot

**无需改代码的 GPU 训练监控 + 钉钉告警工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://www.python.org/)

---

## 功能亮点

- **零侵入监控** — 自动发现 GPU 上的训练进程，无需修改任何训练代码
- **实时状态面板** — 一目了然查看实验名、GPU、epoch 进度、val_acc、MF1 等指标
- **钉钉告警** — 训练完成、异常中断、loss 飙升时自动推送钉钉消息
- **智能日志解析** — 支持多种主流训练日志格式，自动提取关键指标
- **多 Webhook 支持** — 不同实验/团队可配置不同的钉钉群通知
- **守护进程模式** — 后台持续监控，定时巡检，不用手动反复查看
- **历史记录** — 保存训练状态历史，方便回溯分析
- **配置管理** — 导出/导入配置，一键迁移环境

## 快速开始

### 下载安装

```bash
# 下载 trainbot
wget https://raw.githubusercontent.com/MSWEIMZ/train-monitor/main/trainbot -O ~/.local/bin/trainbot

# 添加执行权限
chmod +x ~/.local/bin/trainbot

# 确认 ~/.local/bin 在 PATH 中
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 初始配置

```bash
# 设置钉钉 Webhook（必填）
trainbot config set webhook "https://oapi.dingtalk.com/robot/send?access_token=你的token"

# 设置巡检间隔（秒，默认 300）
trainbot config set interval 300
```

### 开始使用

```bash
# 查看当前所有训练状态
trainbot status

# 启动后台监控（训练完成后自动告警）
trainbot monitor start

# 停止后台监控
trainbot monitor stop
```

## 命令速查

| 命令 | 说明 |
|------|------|
| `trainbot status` | 查看所有训练进程状态 |
| `trainbot monitor start` | 启动后台监控守护进程 |
| `trainbot monitor stop` | 停止后台监控 |
| `trainbot monitor status` | 查看监控守护进程状态 |
| `trainbot config show` | 显示当前配置 |
| `trainbot config set <key> <value>` | 设置配置项 |
| `trainbot config get <key>` | 获取配置项的值 |
| `trainbot config export <file>` | 导出配置到文件 |
| `trainbot config import <file>` | 从文件导入配置 |
| `trainbot history` | 查看训练历史记录 |
| `trainbot history clear` | 清空历史记录 |
| `trainbot log show` | 查看监控日志 |
| `trainbot log clear` | 清空监控日志 |
| `trainbot test` | 发送测试通知（验证 Webhook） |
| `trainbot update` | 更新到最新版本 |
| `trainbot uninstall` | 卸载 trainbot |

## 获取钉钉 Webhook

1. 打开钉钉群，进入 **群设置** > **智能群助手**
2. 点击 **添加机器人**，选择 **自定义（通过 Webhook 接入）**
3. 设置机器人名称（如 "训练监控"），安全设置选择 **自定义关键词**
4. 关键词填写：`训练`（trainbot 的通知消息包含此关键词）
5. 复制生成的 Webhook URL，配置到 trainbot：

```bash
trainbot config set webhook "https://oapi.dingtalk.com/robot/send?access_token=xxxx"
```

## 支持的日志格式

trainbot 能自动识别以下训练日志格式：

**格式 1：带完整指标的 Epoch 日志**
```
Epoch 12/50 | Train 0.6348 0.9998 | Val 0.8152 0.8008 0.7750
```

**格式 2：带 LR 的详细日志**
```
Ep 001 [LR: 1.15e-05] | Train Loss 2.795 Acc 0.061 | Val Loss 2.648 Acc 0.158 | MF1 0.077
```

**格式 3：简洁的 val_loss 日志**
```
Epoch 12 | val_loss=0.112
```

**格式 4：蒸馏 loss 日志**
```
Epoch 39/50 | Train 0.1291 | Val 0.1033
```

## 自定义正则表达式

如果默认格式无法匹配你的日志，可以通过自定义正则表达式扩展：

```bash
# 在配置文件中添加自定义正则
trainbot config set custom_regex 'Epoch\s+(\d+).*?acc[=:]\s*([\d.]+)'
```

正则表达式中使用捕获组 `()` 来提取 epoch 编号和指标值。

## 多 Webhook 配置

当多个团队共用监控平台时，可以为不同实验配置不同的钉钉群通知：

```bash
# 默认 Webhook（所有实验的兜底通知）
trainbot config set webhook "https://oapi.dingtalk.com/robot/send?access_token=default_token"

# 为特定实验组配置专属 Webhook
trainbot config set webhook.exp_a "https://oapi.dingtalk.com/robot/send?access_token=token_a"
trainbot config set webhook.resnet18 "https://oapi.dingtalk.com/robot/send?access_token=token_b"
```

匹配规则：trainbot 会优先查找与实验名匹配的 Webhook，未匹配则使用默认 Webhook。

## 许可证

MIT License
