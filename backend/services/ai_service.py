"""Dịch vụ tích hợp DeepSeek AI thẩm định và vá lỗi mã nguồn (Single-Batch AI Service)."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_AI_ENDPOINT = os.getenv("DEEPSEEK_PROXY_URL", "http://127.0.0.1:8001/chat")
DEFAULT_AI_TIMEOUT = float(os.getenv("AI_SERVICE_TIMEOUT", "90.0"))


def _clean_json_response(raw_text: str) -> dict[str, Any] | None:
    """Trích xuất và phân tích cú pháp JSON an toàn từ phản hồi của mô hình ngôn ngữ."""
    clean = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
    if match:
        clean = match.group(1).strip()

    try:
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    obj_match = re.search(r"(\{[\s\S]*\})", clean)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(1))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    return None


def _call_ai_api(
    endpoint: str,
    prompt: str,
    system_prompt: str = "Chuyên viên phân tích bảo mật & chất lượng mã nguồn",
    timeout: float = DEFAULT_AI_TIMEOUT,
) -> str:
    """Gửi yêu cầu HTTP POST tới cổng proxy AI hoặc OpenAI-compatible API."""
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme URL không hợp lệ: {parsed.scheme}")

    headers = {"Content-Type": "application/json; charset=utf-8"}
    if endpoint.rstrip("/").endswith("/chat"):
        payload_dict = {
            "message": prompt,
            "system_prompt": system_prompt,
            "thinking_enabled": True,
            "new_chat": True,
        }
    else:
        payload_dict = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

    body = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        raw_resp = resp.read().decode("utf-8")

    data = json.loads(raw_resp)
    if isinstance(data, dict):
        if "response" in data:
            return str(data["response"]).strip()
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            first_choice = data["choices"][0]
            if isinstance(first_choice, dict) and "message" in first_choice:
                return str(first_choice["message"].get("content", "")).strip()

    return str(data).strip()


def _heuristic_issue_fix(issue: dict[str, Any]) -> dict[str, str]:
    """Tạo phân tích và gợi ý bản vá heuristic nội bộ cho lỗi cụ thể."""
    msg = str(issue.get("message", "")).lower()
    tool = str(issue.get("tool", "")).lower()
    rule = str(issue.get("rule_code") or "").lower()

    if any(k in msg or k in rule for k in ("eval", "exec", "ast.literal_eval")):
        analysis = (
            "Phát hiện hành vi gọi hàm thực thi mã động (eval/exec). "
            "Đây là lỗ hổng nghiêm trọng có thể dẫn đến thực thi mã từ xa (RCE)."
        )
        triage = "confirmed_risk"
        patch = (
            "# Khuyến nghị: Thay thế hàm thực thi động bằng ast.literal_eval an toàn\n"
            "import ast\n"
            "safe_result = ast.literal_eval(user_input_string)"
        )
    elif any(k in msg or k in rule for k in ("shell=true", "os.system", "subprocess", "popen")):
        analysis = (
            "Lệnh hệ điều hành được gọi kèm shell=True hoặc qua chuỗi nối thô, "
            "tiềm ẩn nguy cơ chèn lệnh hệ thống (Command Injection)."
        )
        triage = "confirmed_risk"
        patch = (
            "# Khuyến nghị: Sử dụng subprocess.run với danh sách tham số và shell=False\n"
            "import subprocess\n"
            "subprocess.run(['command', 'arg1', 'arg2'], check=True, shell=False)"
        )
    elif any(k in msg or k in rule for k in ("password", "secret", "token", "key", "entropy")):
        analysis = (
            "Phát hiện chuỗi bí mật, token hoặc hằng số có độ hỗn loạn Shannon Entropy cao. "
            "Cần tránh hardcode thông tin nhạy cảm vào mã nguồn."
        )
        triage = "confirmed_risk"
        patch = (
            "# Khuyến nghị: Đọc khóa bí mật từ biến môi trường thông qua tệp .env\n"
            "import os\n"
            "api_key = os.getenv('APP_SECRET_KEY', 'default_dev_key')"
        )
    elif any(k in msg or k in rule for k in ("sql", "select", "insert", "update", "delete")):
        analysis = (
            "Truy vấn cơ sở dữ liệu có dấu hiệu định dạng chuỗi trực tiếp, "
            "tiềm ẩn nguy cơ SQL Injection nghiêm trọng."
        )
        triage = "confirmed_risk"
        patch = (
            "# Khuyến nghị: Sử dụng câu lệnh SQL tham số hóa (Parameterized Query)\n"
            "cursor.execute('SELECT * FROM users WHERE username = %s;', (username,))"
        )
    else:
        analysis = (
            f"Cảnh báo vi phạm từ công cụ {tool.upper()} (Mã kiểm thử: {rule or 'N/A'}). "
            "Khuyến nghị rà soát kiểm tra tính toàn vẹn và quy chuẩn lập trình."
        )
        triage = "confirmed_risk"
        patch = (
            "# Khuyến nghị xử lý: Tuân thủ quy chuẩn PEP8 và bọc khối try/except phù hợp\n"
            "try:\n"
            "    # Thực thi an toàn\n"
            "    pass\n"
            "except Exception as exc:\n"
            "    logger.error('Xử lý ngoại lệ an toàn: %s', exc)"
        )

    return {
        "analysis": analysis,
        "triage": triage,
        "fixed_code": patch,
    }


def _heuristic_enrichment(
    session_summary: dict[str, Any],
    issues: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Cung cấp nhận định và bản vá dự phòng khi máy chủ AI ngoại tuyến."""
    total_score = float(session_summary.get("total_score") or 0.0)
    grade = str(session_summary.get("grade") or "C")
    quality_score = float(session_summary.get("quality_score") or total_score)
    security_score = float(session_summary.get("security_score") or total_score)

    has_crit = any(
        str(iss.get("severity", "")).lower() in ("critical", "high") for iss in issues
    )

    verdict = (
        "Cần ưu tiên xử lý các cảnh báo an ninh mức độ Critical và High trước khi triển khai sản phẩm."
        if has_crit
        else "Dự án không có lỗ hổng bảo mật mức nghiêm trọng cao, trạng thái mã nguồn tương đối an toàn."
    )

    session_review = {
        "overview": (
            f"Dự án đạt {total_score:.1f}/100 điểm tổng thể (Xếp loại {grade}). "
            f"Điểm chất lượng mã nguồn: {quality_score:.1f}/100; "
            f"Điểm an toàn bảo mật: {security_score:.1f}/100."
        ),
        "security_verdict": verdict,
        "priority_actions": [
            "Xử lý dứt điểm các đoạn mã thực thi động và gọi lệnh shell hệ thống.",
            "Cập nhật các gói thư viện phụ thuộc có lỗ hổng CVE công bố.",
            "Tái cấu trúc các hàm có chỉ số độ phức tạp Cyclomatic Complexity cao.",
        ],
    }

    for iss in issues:
        sev = str(iss.get("severity", "")).lower()
        if sev in ("critical", "high") and not iss.get("ai_analysis"):
            fix_data = _heuristic_issue_fix(iss)
            iss["ai_analysis"] = fix_data["analysis"]
            iss["ai_triage"] = fix_data["triage"]
            iss["ai_patch"] = fix_data["fixed_code"]

    return session_review, issues


def enrich_session_single_batch(  # pylint: disable=too-many-locals
    session_summary: dict[str, Any],
    issues: list[dict[str, Any]],
    endpoint: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Đóng gói toàn bộ kết quả phân tích theo cơ chế 2 lớp (Single-Batch) và gọi DeepSeek AI.

    Lớp 1 (Critical & High): Gửi đầy đủ thông tin kèm 7 dòng trích đoạn mã lỗi.
    Lớp 2 (Medium & Low): Gửi thông tin tóm tắt để AI nắm bức tranh toàn cảnh mà không tràn token.
    """
    target_endpoint = endpoint or DEFAULT_AI_ENDPOINT

    layer1_items = []
    layer2_items = []
    for idx, iss in enumerate(issues):
        sev = str(iss.get("severity", "medium")).lower()
        base_item = {
            "index": idx,
            "tool": iss.get("tool", ""),
            "severity": sev,
            "rule_code": iss.get("rule_code") or iss.get("test_id") or "",
            "file": iss.get("file_path") or iss.get("file") or "",
            "line": iss.get("line_number") or iss.get("line") or 0,
            "message": iss.get("message", ""),
        }
        if sev in ("critical", "high"):
            base_item["code_snippet"] = iss.get("code_snippet") or ""
            layer1_items.append(base_item)
        else:
            layer2_items.append(base_item)

    prompt_data = {
        "summary": session_summary,
        "critical_and_high_issues": layer1_items,
        "medium_and_low_summary": layer2_items,
    }

    user_prompt = (
        "Bạn là chuyên gia thẩm định chất lượng mã nguồn và an toàn phần mềm Python.\n"
        "Hãy phân tích kết quả quét dưới đây và trả về DUY NHẤT một chuỗi JSON hợp lệ "
        "theo đúng định dạng sau:\n"
        "{\n"
        '  "session_review": {\n'
        '    "overview": "Tóm tắt ngắn gọn chất lượng code và an ninh (tiếng Việt)",\n'
        '    "security_verdict": "Nhận định mức độ an toàn bảo mật (tiếng Việt)",\n'
        '    "priority_actions": ["Hành động ưu tiên 1", "Hành động ưu tiên 2", "Hành động ưu tiên 3"]\n'
        "  },\n"
        '  "issue_fixes": [\n'
        "    {\n"
        '      "index": 0,\n'
        '      "analysis": "Phân tích nguyên nhân và rủi ro thực tế (tiếng Việt)",\n'
        '      "triage": "confirmed_risk" hoặc "likely_false_positive",\n'
        '      "fixed_code": "Đoạn mã code sửa an toàn đề xuất"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "DỮ LIỆU ĐẦU VÀO:\n"
        f"{json.dumps(prompt_data, ensure_ascii=False, indent=2)}"
    )

    try:
        raw_reply = _call_ai_api(
            endpoint=target_endpoint,
            prompt=user_prompt,
            system_prompt="Chuyên gia DevSecOps thẩm định mã nguồn và vá lỗi tự động",
        )
        parsed = _clean_json_response(raw_reply)
        if parsed and isinstance(parsed.get("session_review"), dict):
            session_review = parsed["session_review"]
            fixes = parsed.get("issue_fixes", [])
            for fix in fixes:
                if isinstance(fix, dict) and "index" in fix:
                    fix_idx = fix["index"]
                    if 0 <= fix_idx < len(issues):
                        issues[fix_idx]["ai_analysis"] = str(fix.get("analysis", "")).strip()
                        issues[fix_idx]["ai_triage"] = str(
                            fix.get("triage", "confirmed_risk")
                        ).strip()
                        issues[fix_idx]["ai_patch"] = str(fix.get("fixed_code", "")).strip()

            return session_review, issues

        logger.warning("Phản hồi AI không đúng định dạng JSON yêu cầu, chuyển heuristic fallback.")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Không thể kết nối máy chủ AI (%s): %s. Dùng heuristic fallback.", target_endpoint, exc)

    return _heuristic_enrichment(session_summary, issues)


def explain_single_issue(
    issue: dict[str, Any],
    endpoint: str | None = None,
) -> dict[str, str]:
    """Phân tích chuyên sâu một lỗi riêng lẻ theo yêu cầu người dùng."""
    target_endpoint = endpoint or DEFAULT_AI_ENDPOINT

    user_prompt = (
        "Phân tích chuyên sâu lỗi mã nguồn Python dưới đây và trả về DUY NHẤT một chuỗi JSON hợp lệ:\n"
        "{\n"
        '  "analysis": "Giải thích chi tiết nguyên nhân và nguy cơ an ninh (tiếng Việt)",\n'
        '  "triage": "confirmed_risk" hoặc "likely_false_positive",\n'
        '  "fixed_code": "Mã nguồn đã sửa chữa an toàn"\n'
        "}\n\n"
        f"Công cụ: {issue.get('tool', 'N/A')}\n"
        f"Mã lỗi: {issue.get('rule_code') or issue.get('test_id') or 'N/A'}\n"
        f"Mức độ: {issue.get('severity', 'N/A')}\n"
        f"Tệp: {issue.get('file_path', 'N/A')}:{issue.get('line_number', 'N/A')}\n"
        f"Thông điệp: {issue.get('message', '')}\n"
        f"Đoạn mã:\n{issue.get('code_snippet', '')}"
    )

    try:
        raw_reply = _call_ai_api(
            endpoint=target_endpoint,
            prompt=user_prompt,
            system_prompt="Chuyên viên kiểm định bảo mật mã nguồn",
        )
        parsed = _clean_json_response(raw_reply)
        if parsed and "analysis" in parsed and "fixed_code" in parsed:
            return {
                "ai_analysis": str(parsed["analysis"]).strip(),
                "ai_triage": str(parsed.get("triage", "confirmed_risk")).strip(),
                "ai_patch": str(parsed["fixed_code"]).strip(),
            }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Gọi AI giải thích lỗi lẻ thất bại (%s): %s", target_endpoint, exc)

    fallback_fix = _heuristic_issue_fix(issue)
    return {
        "ai_analysis": fallback_fix["analysis"],
        "ai_triage": fallback_fix["triage"],
        "ai_patch": fallback_fix["fixed_code"],
    }


def check_ai_health(endpoint: str | None = None) -> dict[str, Any]:
    """Kiểm tra máy chủ AI proxy có đang trực tuyến và phản hồi hay không."""
    target = (endpoint or DEFAULT_AI_ENDPOINT).strip()
    health_url = target
    if target.endswith("/chat"):
        health_url = target[:-5] + "/health"
    elif target.endswith("/v1/chat/completions"):
        health_url = target.replace("/v1/chat/completions", "/health")

    parsed = urllib.parse.urlparse(health_url)
    if parsed.scheme not in ("http", "https"):
        return {"status": "error", "message": f"Scheme không hợp lệ: {parsed.scheme}"}

    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=3.0) as resp:  # nosec B310
            body = resp.read().decode("utf-8")
        data = json.loads(body)
        mode = data.get("mode") or data.get("status") or "online"
        return {
            "status": "ok",
            "available": True,
            "mode": str(mode),
            "message": "Máy chủ DeepSeek AI đang hoạt động bình thường",
            "data": data,
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "status": "error",
            "available": False,
            "mode": "offline",
            "message": f"Không thể kết nối tới {health_url}: {exc}",
        }
