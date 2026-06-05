# train-monitor (tm)

GPU训练监控工具：自动发现训练进程，显示epoch/loss/acc状态。

## 功能

- 自动发现GPU上的训练进程
- 显示实验名、GPU、epoch进度、val_acc/val_mf1/loss
- 自动从日志开头提取实验描述
- 支持多种日志格式
- 北京时间显示

## 安装

```bash
# 下载脚本
wget https://raw.githubusercontent.com/MSWEIMZ/train-monitor/main/train_monitor -O ~/.local/bin/train_monitor

# 添加执行权限
chmod +x ~/.local/bin/train_monitor

# 添加别名（可选）
echo 'alias tm="train_monitor"' >> ~/.bashrc
source ~/.bashrc
```

## 使用

```bash
# 直接运行
train_monitor

# 或使用别名
tm
```

## 输出示例

```
══════════════════════════════════════════════════════════════════════════════
  train_monitor   2026-01-15 14:30:25
══════════════════════════════════════════════════════════════════════════════

  Experiment           GPU      Epoch      Val Acc    Val MF1    Description
  ──────────────────── ──────── ────────── ────────── ────────── ──────────────────────────────
  exp_a                cuda:0   35/100     92.3%      89.1%      Experiment A: baseline model
  exp_b                cuda:1   18/50      88.7%      85.2%      Experiment B: with augmentation
  exp_c                cuda:2   42/50      loss:0.032 -          Experiment C: knowledge distillation
```

## 支持的日志格式

- `Epoch X/Y` 开头的训练日志
- `Ep X` 开头的训练日志
- 包含 `Val Loss`、`Val Acc`、`MF1` 等指标的日志
- 日志开头在 `=====` 之间的实验描述

## 工作原理

1. 通过 `ps` 命令查找当前用户的Python训练进程
2. 从 `/proc/pid/fd/1` 获取日志文件路径
3. 解析日志最后100行，提取最新epoch信息
4. 从日志开头提取实验描述（在 `=====` 之间的文本）

## 依赖

- Python 3.6+
- Linux (需要 `/proc` 文件系统)

## License

MIT
