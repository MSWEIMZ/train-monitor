"""trainbot 单元测试"""
import sys
import os
import importlib.util
import importlib.machinery

import pytest

# trainbot没有.py后缀，需要用SourceFileLoader加载
_trainbot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trainbot")
_loader = importlib.machinery.SourceFileLoader("trainbot", _trainbot_path)
_spec = importlib.util.spec_from_loader("trainbot", _loader)
_trainbot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_trainbot)

DEFAULT_CONFIG = _trainbot.DEFAULT_CONFIG
extract_exp_name = _trainbot.extract_exp_name
check_anomaly = _trainbot.check_anomaly
check_acc_anomaly = _trainbot.check_acc_anomaly
check_nan = _trainbot.check_nan


class TestDefaultConfig:
    """测试DEFAULT_CONFIG包含所有必需的键"""

    def test_has_webhook_url(self):
        assert "webhook_url" in DEFAULT_CONFIG

    def test_has_webhook_type(self):
        assert "webhook_type" in DEFAULT_CONFIG

    def test_has_notify_format(self):
        assert "notify_format" in DEFAULT_CONFIG

    def test_has_notify_on_complete(self):
        assert "notify_on_complete" in DEFAULT_CONFIG

    def test_has_notify_on_anomaly(self):
        assert "notify_on_anomaly" in DEFAULT_CONFIG

    def test_has_anomaly_loss_spike(self):
        assert "anomaly_loss_spike" in DEFAULT_CONFIG

    def test_has_anomaly_acc_drop(self):
        assert "anomaly_acc_drop" in DEFAULT_CONFIG

    def test_has_monitor_interval(self):
        assert "monitor_interval" in DEFAULT_CONFIG

    def test_has_monitor_mode(self):
        assert "monitor_mode" in DEFAULT_CONFIG

    def test_has_log_dir(self):
        assert "log_dir" in DEFAULT_CONFIG

    def test_has_custom_patterns(self):
        assert "custom_patterns" in DEFAULT_CONFIG

    def test_has_max_history(self):
        assert "max_history" in DEFAULT_CONFIG

    def test_webhook_type_default(self):
        assert DEFAULT_CONFIG["webhook_type"] == "normal"

    def test_monitor_interval_is_positive(self):
        assert DEFAULT_CONFIG["monitor_interval"] > 0


class TestExtractExpName:
    """测试实验名提取"""

    def test_simple_python_script(self):
        cmdline = "python train_my_model.py --epochs 50"
        result = extract_exp_name(cmdline)
        assert result == "my_model"

    def test_python3_script(self):
        cmdline = "python3 train_cnn.py --batch-size 32"
        result = extract_exp_name(cmdline)
        assert result == "cnn"

    def test_script_without_train_prefix(self):
        cmdline = "python run_experiment.py --lr 0.001"
        result = extract_exp_name(cmdline)
        assert result == "run_experiment"

    def test_name_param_fallback(self):
        """当没有脚本名时，--name参数作为后备"""
        cmdline = "python3 --name my_exp_001"
        result = extract_exp_name(cmdline)
        assert result == "my_exp_001"

    def test_script_name_priority_over_name_param(self):
        """脚本名优先于--name参数（与train_monitor行为一致）"""
        cmdline = "python some_script.py --name my_exp_001"
        result = extract_exp_name(cmdline)
        assert result == "some_script"

    def test_no_script_found(self):
        cmdline = "some_random_command"
        result = extract_exp_name(cmdline)
        assert result == "unknown"

    def test_full_path_script(self):
        cmdline = "python /home/user/projects/train_resnet.py --gpu 0"
        result = extract_exp_name(cmdline)
        assert result == "resnet"


class TestCheckAnomaly:
    """测试loss突增检测"""

    def test_no_anomaly(self):
        history = [0.5, 0.4, 0.3, 0.35]
        is_anomaly, ratio = check_anomaly(history, threshold=2.0)
        assert is_anomaly is False

    def test_loss_spike(self):
        history = [0.3, 0.9]
        is_anomaly, ratio = check_anomaly(history, threshold=2.0)
        assert is_anomaly is True
        assert ratio == pytest.approx(3.0)

    def test_threshold_boundary(self):
        # 恰好等于阈值，不算异常
        history = [0.5, 1.0]
        is_anomaly, ratio = check_anomaly(history, threshold=2.0)
        assert is_anomaly is False

    def test_empty_history(self):
        is_anomaly, ratio = check_anomaly([])
        assert is_anomaly is False

    def test_single_value(self):
        is_anomaly, ratio = check_anomaly([0.5])
        assert is_anomaly is False

    def test_zero_prev_value(self):
        history = [0.0, 0.5]
        is_anomaly, ratio = check_anomaly(history, threshold=2.0)
        assert is_anomaly is False


class TestCheckAccAnomaly:
    """测试准确率下降检测"""

    def test_no_anomaly(self):
        history = [0.8, 0.79]
        is_anomaly, drop = check_acc_anomaly(history, threshold=0.1)
        assert is_anomaly is False

    def test_acc_drop(self):
        history = [0.9, 0.5]
        is_anomaly, drop = check_acc_anomaly(history, threshold=0.1)
        assert is_anomaly is True
        assert drop == pytest.approx(0.4)

    def test_below_threshold(self):
        history = [0.8, 0.71]
        is_anomaly, drop = check_acc_anomaly(history, threshold=0.1)
        assert is_anomaly is False  # drop = 0.09 < 0.1

    def test_empty_history(self):
        is_anomaly, drop = check_acc_anomaly([])
        assert is_anomaly is False

    def test_single_value(self):
        is_anomaly, drop = check_acc_anomaly([0.8])
        assert is_anomaly is False

    def test_improving_acc(self):
        history = [0.7, 0.9]
        is_anomaly, drop = check_acc_anomaly(history, threshold=0.1)
        assert is_anomaly is False


class TestCheckNan:
    """测试NaN/Inf检测"""

    def test_no_nan(self):
        assert check_nan([0.5, 0.3, 0.1]) is False

    def test_detect_nan(self):
        assert check_nan([0.5, float("nan"), 0.1]) is True

    def test_detect_inf(self):
        assert check_nan([0.5, float("inf"), 0.1]) is True

    def test_detect_neg_inf(self):
        assert check_nan([0.5, float("-inf"), 0.1]) is True

    def test_empty_list(self):
        assert check_nan([]) is False

    def test_none_values(self):
        assert check_nan([0.5, None, 0.1]) is False

    def test_mixed_values(self):
        assert check_nan([1, 2, None, float("nan")]) is True
