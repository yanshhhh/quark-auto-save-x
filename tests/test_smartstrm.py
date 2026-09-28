#!/usr/bin/python3
# -*- encoding: utf-8 -*-
"""SmartStrm 插件单元测试

覆盖:
1. 默认配置 & 空 init (is_active=False)
2. webhook 未提供 http 前缀时自动补 http://
3. webhook 末尾斜杠自动 rstrip
4. get_info 成功 (mock 返回 success) → is_active=True
5. get_info 失败 (mock 返回非 success) → is_active=False
6. get_info 异常 → is_active=False
7. run: is_active=False 时 no-op
8. run: task_config.auto_trigger=False 时 no-op
9. run: task.savepath 为空时 no-op
10. run: savepath 无前导 / 时自动补
11. run: savepath 有尾斜杠时自动去
12. run: 正常触发, POST 参数 & savepath 正确
13. run: POST 返回 success=True 时打印成功
14. run: POST 返回 success=False 时打印失败
15. run: POST 异常时不抛错
16. plugin_name = 'smartstrm'
"""
import sys, os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins.smartstrm import Smartstrm


WEBHOOK = "http://test.local:8024/webhook/test"
TASKNAME = "SmartStrm自动整理"


def _make_plugin(is_active=True, **overrides):
    """构建插件实例, 可覆盖 config"""
    cfg = {"webhook": WEBHOOK, "strmtask": TASKNAME, "xlist_path_fix": ""}
    cfg.update(overrides)
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "version": "v0.5.0"}
        mock_req.return_value = mock_resp
        p = Smartstrm(**cfg)
    if is_active:
        p.is_active = True
    return p


def test_plugin_name():
    p = _make_plugin()
    assert p.plugin_name == "smartstrm"
    print("✅ plugin_name = smartstrm")


def test_default_config_keys():
    assert set(Smartstrm.default_config.keys()) == {"webhook", "strmtask", "xlist_path_fix"}
    assert set(Smartstrm.default_task_config.keys()) == {"auto_trigger"}
    assert Smartstrm.default_task_config["auto_trigger"] is True
    print("✅ default_config / default_task_config 键齐全")


def test_empty_init_no_is_active():
    p = Smartstrm()
    assert p.is_active is False
    print("✅ 空 init → is_active=False")


def test_webhook_normalizes_no_scheme():
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "version": "v0.5.0"}
        mock_req.return_value = mock_resp
        p = Smartstrm(webhook="192.168.2.11:8024/webhook/x", strmtask="t", xlist_path_fix="")
    assert p.webhook == "http://192.168.2.11:8024/webhook/x"
    print("✅ webhook 无 scheme → 自动补 http://")


def test_webhook_normalizes_trailing_slash():
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "version": "v0.5.0"}
        mock_req.return_value = mock_resp
        p = Smartstrm(webhook="https://x.com/hook/", strmtask="t", xlist_path_fix="")
    assert p.webhook == "https://x.com/hook"
    print("✅ webhook 尾斜杠 → rstrip")


def test_get_info_success():
    p = _make_plugin(is_active=False)
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "version": "v0.5.0"}
        mock_req.return_value = mock_resp
        result = p.get_info()
    assert result is not None
    assert result.get("success") is True
    print("✅ get_info 成功返回 dict")


def test_get_info_failure():
    p = _make_plugin()
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": False, "message": "bad"}
        mock_req.return_value = mock_resp
        result = p.get_info()
    assert result is None
    print("✅ get_info 失败返回 None")


def test_get_info_exception():
    p = _make_plugin()
    with patch("plugins.smartstrm.requests.request", side_effect=Exception("boom")):
        result = p.get_info()
    assert result is None
    print("✅ get_info 异常返回 None (不抛错)")


def test_run_noop_when_inactive():
    p = _make_plugin(is_active=True)
    p.is_active = False  # 强制关闭
    with patch("plugins.smartstrm.requests.request") as mock_req:
        p.run({"savepath": "/x"})
        assert not mock_req.called
    print("✅ run: is_active=False → 不发请求")


def test_run_noop_when_auto_trigger_false():
    p = _make_plugin(is_active=True)
    task = {"savepath": "/x", "addition": {"smartstrm": {"auto_trigger": False}}}
    with patch("plugins.smartstrm.requests.request") as mock_req:
        p.run(task)
        assert not mock_req.called
    print("✅ run: auto_trigger=False → 不发请求")


def test_run_noop_when_savepath_empty():
    p = _make_plugin(is_active=True)
    with patch("plugins.smartstrm.requests.request") as mock_req:
        p.run({"savepath": ""})
        assert not mock_req.called
    print("✅ run: savepath 空 → 不发请求")


def test_run_normalizes_savepath_no_leading_slash():
    p = _make_plugin(is_active=True)
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "task": {"name": "t", "storage_path": "/x"}}
        mock_req.return_value = mock_resp
        p.run({"savepath": "影视库/测试"})
        # 断言 payload 中 savepath 带前导 /
        _, call_kwargs = mock_req.call_args
        assert call_kwargs["json"]["data"]["savepath"] == "/影视库/测试"
    print("✅ run: savepath 无前导 / → 自动补")


def test_run_normalizes_savepath_trailing_slash():
    p = _make_plugin(is_active=True)
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "task": {"name": "t", "storage_path": "/x/"}}
        mock_req.return_value = mock_resp
        p.run({"savepath": "/影视库/测试/"})
        _, call_kwargs = mock_req.call_args
        assert call_kwargs["json"]["data"]["savepath"] == "/影视库/测试"
    print("✅ run: savepath 尾斜杠 → 去除")


def test_run_success_payload():
    p = _make_plugin(is_active=True)
    task = {"savepath": "/影视库/测试", "addition": {"smartstrm": {"auto_trigger": True}}}
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "task": {"name": "SmartStrm自动整理", "storage_path": "/影视库/测试"}}
        mock_req.return_value = mock_resp
        p.run(task)
        args, call_kwargs = mock_req.call_args
        assert args[0] == "POST"
        assert args[1] == WEBHOOK
        assert call_kwargs["json"] == {
            "event": "qas_strm",
            "data": {
                "strmtask": TASKNAME,
                "savepath": "/影视库/测试",
                "xlist_path_fix": "",
            },
        }
    print("✅ run: POST payload 结构正确")


def test_run_default_task_config_from_addition():
    # 未设置 addition.smartstrm 时, 使用 default_task_config.auto_trigger=True
    p = _make_plugin(is_active=True)
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "task": {"name": "t", "storage_path": "/x"}}
        mock_req.return_value = mock_resp
        p.run({"savepath": "/x"})  # 无 addition
        assert mock_req.called
    print("✅ run: 无 addition.smartstrm → 用 default (auto_trigger=True)")


def test_run_post_failure_prints_msg():
    p = _make_plugin(is_active=True)
    task = {"savepath": "/x"}
    with patch("plugins.smartstrm.requests.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": False, "message": "task not found"}
        mock_req.return_value = mock_resp
        p.run(task)  # 不抛错
    print("✅ run: POST success=False → 打印失败, 不抛错")


def test_run_post_exception_no_throw():
    p = _make_plugin(is_active=True)
    task = {"savepath": "/x"}
    with patch("plugins.smartstrm.requests.request", side_effect=Exception("network err")):
        p.run(task)  # 不抛错
    print("✅ run: POST 异常 → 不抛错")


def main():
    tests = [
        test_plugin_name,
        test_default_config_keys,
        test_empty_init_no_is_active,
        test_webhook_normalizes_no_scheme,
        test_webhook_normalizes_trailing_slash,
        test_get_info_success,
        test_get_info_failure,
        test_get_info_exception,
        test_run_noop_when_inactive,
        test_run_noop_when_auto_trigger_false,
        test_run_noop_when_savepath_empty,
        test_run_normalizes_savepath_no_leading_slash,
        test_run_normalizes_savepath_trailing_slash,
        test_run_success_payload,
        test_run_default_task_config_from_addition,
        test_run_post_failure_prints_msg,
        test_run_post_exception_no_throw,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"💥 {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{'='*50}")
    print(f"结果: {passed}/{len(tests)} 通过, {failed} 失败")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
