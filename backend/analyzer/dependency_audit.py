"""Module kiểm tra lỗ hổng bảo mật CVE trong thư viện phụ thuộc bằng pip-audit."""

import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

_CRITICAL_KEYWORDS = frozenset({
    "critical",
    "remote code execution",
    "rce",
    "arbitrary code",
    "arbitrary command",
    "command injection",
    "sql injection",
})

_NETWORK_KEYWORDS = (
    "connection",
    "network",
    "timeout",
    "temporary failure",
    "getaddrinfo",
    "failed to establish",
    "proxy",
    "socket",
    "unreachable",
)


def _determine_severity(description: str, vuln_id: str) -> str:
    """Xác định mức độ nghiêm trọng (Critical hoặc High) dựa trên mã và mô tả lỗi."""
    text_to_check = f"{vuln_id} {description}".lower()
    if any(keyword in text_to_check for keyword in _CRITICAL_KEYWORDS):
        return "Critical"
    return "High"


def _format_vuln_issue(
    package: str,
    installed_version: str,
    vuln: dict[str, Any],
    rel_file: str,
) -> dict[str, Any]:
    """Chuẩn hóa một lỗ hổng CVE từ pip-audit sang định dạng issue chuẩn của hệ thống."""
    vuln_id = vuln.get("id", "")
    fix_versions = vuln.get("fix_versions") or []
    description = vuln.get("description", "")

    severity = _determine_severity(description, vuln_id)
    fix_str = ", ".join(fix_versions) if fix_versions else "Chưa có bản vá chính thức"
    message = (
        f"Thư viện {package}=={installed_version} dính lỗ hổng {vuln_id}. "
        f"Bản vá khuyến nghị: {fix_str}."
    )

    return {
        "tool": "pip-audit",
        "file": rel_file,
        "line": 0,
        "test_id": vuln_id,
        "severity": severity,
        "package": package,
        "installed_version": installed_version,
        "vuln_id": vuln_id,
        "fix_versions": fix_versions,
        "description": description,
        "message": message,
    }


def _locate_requirements(target_path: str | Path) -> tuple[Path, Path]:
    """Tìm kiếm file requirements.txt và thư mục gốc của target."""
    target = Path(target_path).resolve()
    if target.is_file() and target.name == "requirements.txt":
        return target, target.parent
    if target.is_dir():
        return target / "requirements.txt", target
    return target / "requirements.txt", target.parent


def _parse_audit_output(
    stdout_content: str,
    req_file: Path,
    root_dir: Path,
) -> list[dict[str, Any]]:
    """Giải mã JSON từ pip-audit và trả về danh sách các lỗi đã chuẩn hóa."""
    if not stdout_content:
        return []

    data = json.loads(stdout_content)
    try:
        rel_file = str(req_file.relative_to(root_dir)).replace("\\", "/")
    except ValueError:
        rel_file = os.path.relpath(str(req_file), str(root_dir)).replace("\\", "/")

    issues: list[dict[str, Any]] = []
    for dep in data.get("dependencies", []):
        pkg = dep.get("name", "")
        ver = dep.get("version", "")
        for vuln in dep.get("vulns") or []:
            issues.append(_format_vuln_issue(pkg, ver, vuln, rel_file))
    return issues


def _build_failure_response(stderr_content: str) -> dict[str, Any]:
    """Tạo response khi tiến trình pip-audit gặp sự cố mạng hoặc lỗi runtime."""
    err_lower = stderr_content.lower()
    if any(k in err_lower for k in _NETWORK_KEYWORDS):
        msg = (
            "Không thể kết nối cơ sở dữ liệu PyPA/CVE (lỗi mạng hoặc máy chủ không phản hồi): "
            f"{stderr_content}"
        )
    else:
        msg = f"pip-audit kết thúc với cảnh báo: {stderr_content}"

    return {
        "status": "warning",
        "message": msg,
        "total_issues": 0,
        "issues": [],
    }


def audit_dependencies(
    target_path: str | Path,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """
    Kiểm tra lỗ hổng bảo mật CVE trong file requirements.txt của dự án.

    Args:
        target_path: Thư mục dự án hoặc đường dẫn trực tiếp tới file requirements.txt.
        timeout_seconds: Thời gian chờ tối đa kết nối và truy vấn (mặc định 60s).

    Returns:
        dict kết quả quét theo định dạng chuẩn:
        {
            "status": "ok" | "warning" | "error",
            "total_issues": int,
            "issues": list[dict],
            "message": str (tùy chọn)
        }
    """
    req_file, root_dir = _locate_requirements(target_path)

    # 1. Nếu không tìm thấy file requirements.txt, bỏ qua an toàn
    if not req_file.exists():
        return {
            "status": "ok",
            "message": "Không tìm thấy requirements.txt, bỏ qua kiểm tra CVE phụ thuộc",
            "total_issues": 0,
            "issues": [],
        }

    # 2. Dò tìm lệnh thực thi pip-audit
    pip_audit_exec = shutil.which("pip-audit") or "pip-audit"
    cmd = [pip_audit_exec, "-r", str(req_file), "-f", "json"]

    try:
        # 3. Thực thi an toàn qua subprocess (shell=False)
        process = subprocess.run(  # nosec B603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )

        stdout_content = (process.stdout or "").strip()
        stderr_content = (process.stderr or "").strip()

        # Kiểm tra lỗi mạng hoặc mất kết nối máy chủ CVE
        if process.returncode != 0 and not stdout_content:
            return _build_failure_response(stderr_content)

        issues = _parse_audit_output(stdout_content, req_file, root_dir)
        return {
            "status": "ok",
            "total_issues": len(issues),
            "issues": issues,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "warning",
            "message": "Quá thời gian kết nối cơ sở dữ liệu PyPA/CVE",
            "total_issues": 0,
            "issues": [],
        }
    except FileNotFoundError as exc:
        return {
            "status": "error",
            "message": f"Không tìm thấy công cụ pip-audit trên hệ thống: {exc}",
            "total_issues": 0,
            "issues": [],
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "status": "error",
            "message": str(exc),
            "total_issues": 0,
            "issues": [],
        }


if __name__ == "__main__":
    sample_dir = Path(__file__).resolve().parents[1] / "samples" / "bad_project"
    print(f"[*] Đang thực hiện kiểm tra CVE phụ thuộc vào: {sample_dir}")
    audit_result = audit_dependencies(sample_dir)
    print(json.dumps(audit_result, indent=2, ensure_ascii=False))
