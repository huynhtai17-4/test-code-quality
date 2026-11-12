"""Module quản lý nạp và chuẩn bị mã nguồn vào workspace an toàn."""

import os
import shutil
import stat
import subprocess  # nosec B404
import uuid
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[1] / "workspace"


def extract_zip_safe(zip_path: str | Path, extract_to: str | Path) -> Path:
    """
    Giải nén file zip vào thư mục đích với cơ chế chống tấn công Zip Slip.

    Args:
        zip_path: Đường dẫn tới file zip cần giải nén.
        extract_to: Thư mục đích sẽ chứa mã nguồn sau khi giải nén.

    Returns:
        Path: Đường dẫn tuyệt đối tới thư mục đã giải nén.

    Raises:
        ValueError: Nếu phát hiện tệp con có đường dẫn thoát ra ngoài extract_to.
        FileNotFoundError: Nếu file zip không tồn tại.
    """
    zip_file_path = Path(zip_path).resolve()
    if not zip_file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file zip: {zip_path}")

    dest_dir = Path(extract_to).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_file_path, "r") as archive:
        for member in archive.infolist():
            # Kiểm tra đường dẫn tuyệt đối của từng file con
            target_file = (dest_dir / member.filename).resolve()
            if not target_file.is_relative_to(dest_dir):
                raise ValueError(
                    f"Phát hiện nguy cơ tấn công Zip Slip! File '{member.filename}' "
                    f"nằm ngoài thư mục đích: {dest_dir}"
                )
        archive.extractall(dest_dir)

    return dest_dir


def clone_git_repo(
    repo_url: str,
    target_dir: str | Path,
    timeout_seconds: int = 120,
) -> Path:
    """
    Clone nông một Git repository (--depth 1) vào thư mục đích.

    Args:
        repo_url: Địa chỉ URL của Git repository.
        target_dir: Thư mục đích nhận mã nguồn clone về.
        timeout_seconds: Thời gian chờ tối đa cho lệnh git clone (mặc định 120s).

    Returns:
        Path: Đường dẫn thư mục đã clone thành công.
    """
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    git_exec = shutil.which("git")
    if not git_exec:
        raise FileNotFoundError("Không tìm thấy lệnh git trên hệ thống (vui lòng cài đặt Git).")

    clean_url = str(repo_url).strip()
    cmd = [git_exec, "clone", "--depth", "1", clean_url, str(target_path)]

    try:
        process = subprocess.run(  # nosec B603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        if process.returncode != 0:
            stderr_msg = (process.stderr or process.stdout or "").strip()
            raise RuntimeError(f"Lỗi khi clone Git repository ({clean_url}): {stderr_msg}")
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            f"Quá thời gian ({timeout_seconds}s) khi clone Git repository: {clean_url}"
        ) from exc

    return target_path


def cleanup_workspace(target_dir: str | Path) -> None:
    """
    Xóa thư mục làm việc tạm thời sau khi phân tích xong.

    Tự động gỡ bỏ thuộc tính read-only để tránh lỗi xung đột trên Windows (đặc biệt thư mục .git).
    """
    path = Path(target_dir).resolve()
    if not path.exists():
        return

    # Gỡ thuộc tính read-only trên Windows
    for root, dirs, files in os.walk(path):
        for fname in files:
            full_file = os.path.join(root, fname)
            try:
                os.chmod(full_file, stat.S_IWRITE)
            except OSError:
                pass
        for dname in dirs:
            full_dir = os.path.join(root, dname)
            try:
                os.chmod(full_dir, stat.S_IWRITE)
            except OSError:
                pass

    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


def _prepare_local_dir(source_path: str) -> dict[str, Any]:
    """Xử lý nạp mã nguồn từ thư mục cục bộ có sẵn."""
    local_path = Path(source_path).resolve()
    if not local_path.exists():
        return {
            "status": "error",
            "message": f"Thư mục cục bộ không tồn tại: {source_path}",
        }
    if not local_path.is_dir():
        return {
            "status": "error",
            "message": f"Đường dẫn không phải là thư mục: {source_path}",
        }
    return {
        "status": "ok",
        "working_dir": str(local_path),
        "cleanup_needed": False,
    }


def _prepare_zip(zip_path: str, ws_root: Path) -> dict[str, Any]:
    """Xử lý giải nén file zip vào workspace tạm."""
    zip_file = Path(zip_path).resolve()
    if not zip_file.exists():
        return {"status": "error", "message": f"File zip không tồn tại: {zip_path}"}
    if not zip_file.is_file():
        return {"status": "error", "message": f"Đường dẫn không phải là file zip: {zip_path}"}

    target_ws = ws_root / f"zip_{uuid.uuid4().hex[:10]}"
    try:
        extracted_dir = extract_zip_safe(zip_file, target_ws)
        return {
            "status": "ok",
            "working_dir": str(extracted_dir),
            "cleanup_needed": True,
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        cleanup_workspace(target_ws)
        return {"status": "error", "message": f"Lỗi giải nén file zip: {exc}"}


def _prepare_github(repo_url: str, ws_root: Path) -> dict[str, Any]:
    """Xử lý clone repository GitHub vào workspace tạm."""
    target_ws = ws_root / f"git_{uuid.uuid4().hex[:10]}"
    try:
        cloned_dir = clone_git_repo(repo_url, target_ws)
        return {
            "status": "ok",
            "working_dir": str(cloned_dir),
            "cleanup_needed": True,
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        cleanup_workspace(target_ws)
        return {"status": "error", "message": f"Lỗi clone Git repository: {exc}"}


def prepare_source(
    source_type: str,
    source_path: str,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """
    Điều phối nạp mã nguồn vào workspace làm việc an toàn.

    Args:
        source_type: Nhận "local_dir", "zip", hoặc "github".
        source_path: Đường dẫn thư mục, đường dẫn file zip hoặc URL Git repository.
        workspace_root: Thư mục chứa workspace tạm (mặc định backend/workspace).

    Returns:
        dict: {"status": "ok", "working_dir": str, "cleanup_needed": bool}
        hoặc: {"status": "error", "message": str}
    """
    ws_root = Path(workspace_root).resolve() if workspace_root else DEFAULT_WORKSPACE_ROOT
    ws_root.mkdir(parents=True, exist_ok=True)

    normalized_type = str(source_type).strip().lower()
    if normalized_type == "local_dir":
        return _prepare_local_dir(source_path)
    if normalized_type == "zip":
        return _prepare_zip(source_path, ws_root)
    if normalized_type == "github":
        return _prepare_github(source_path, ws_root)

    return {
        "status": "error",
        "message": (
            f"Loại nguồn không hỗ trợ: '{source_type}'. "
            "Chỉ chấp nhận 'local_dir', 'zip', hoặc 'github'."
        ),
    }


def _run_sample_test() -> None:
    """Khối kiểm nghiệm nén và giải nén an toàn bad_project."""
    sample_src = Path(__file__).resolve().parents[1] / "samples" / "bad_project"
    test_ws = DEFAULT_WORKSPACE_ROOT / "test_run"
    test_ws.mkdir(parents=True, exist_ok=True)

    temp_zip = test_ws / "bad_project_test.zip"
    extract_target = test_ws / "extracted_project"

    print(f"[*] 1. Đang nén thư mục '{sample_src}' thành '{temp_zip}'...")
    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(sample_src):
            for file in files:
                abs_file = Path(root) / file
                rel_arc = abs_file.relative_to(sample_src)
                zf.write(abs_file, rel_arc)

    print(f"[+] 2. Đang giải nén an toàn qua extract_zip_safe tới '{extract_target}'...")
    extracted_path = extract_zip_safe(temp_zip, extract_target)

    extracted_files = [f.name for f in extracted_path.iterdir() if f.is_file()]
    print(f"[+] 3. Giải nén thành công! Các tệp giải nén được: {extracted_files}")

    print("[*] 4. Đang dọn dẹp thư mục làm việc tạm thời...")
    cleanup_workspace(test_ws)
    print("[OK] Đã dọn dẹp sạch sẽ toàn bộ thư mục tạm. Kiểm thử hoàn tất thành công!")


if __name__ == "__main__":
    _run_sample_test()
