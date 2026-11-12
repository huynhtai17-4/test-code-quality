"""Kiểm thử tự động toàn diện nhóm Widget dùng chung (Step 2 - SKILLS.md)."""

import sys
from pathlib import Path

# Đảm bảo import được toàn bộ package từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from PyQt6.QtWidgets import QApplication  # pylint: disable=no-name-in-module

from frontend.views.theme import (
    SEV_CRITICAL,
    STATUS_COLORS,
    TEN_TIEU_CHI,
)
from frontend.views.widgets import (
    EmptyState,
    GradeLabel,
    InlineNotice,
    ScoreBar,
    SeverityBadge,
    StatusDot,
)

_APP = QApplication.instance() or QApplication(sys.argv)


def test_severity_badge() -> None:
    """Kiểm tra widget SeverityBadge."""
    # 1. Khởi tạo mặc định
    badge = SeverityBadge("Critical", show_vietnamese=True)
    if badge.text() != "Nghiêm trọng":
        raise RuntimeError(f"SeverityBadge text không đúng: {badge.text()}")
    if SEV_CRITICAL not in badge.styleSheet():
        raise RuntimeError("SeverityBadge không chứa mã màu SEV_CRITICAL")

    # 2. Chế độ tiếng Anh
    badge_en = SeverityBadge("High", show_vietnamese=False)
    if badge_en.text() != "High":
        raise RuntimeError(f"SeverityBadge EN text không đúng: {badge_en.text()}")

    # 3. Chuyển đổi trạng thái động
    badge.set_severity("thấp")
    if badge.text() != "Thấp":
        raise RuntimeError(f"SeverityBadge set_severity không đúng: {badge.text()}")

    # 4. Fallback khi nhận giá trị không xác định
    badge.set_severity("unknown_level")
    if badge.text() != "Thấp":
        raise RuntimeError("SeverityBadge fallback thất bại")


def test_status_dot() -> None:
    """Kiểm tra widget StatusDot."""
    dot = StatusDot("open")
    if dot.findChild(object) is None:
        raise RuntimeError("StatusDot không chứa phần tử con")

    # Kiểm tra chuyển đổi trạng thái
    for status_key, expected_color in STATUS_COLORS.items():
        dot.set_status(status_key)
        internal_dot = getattr(dot, "_dot", None)
        if internal_dot is None or internal_dot.color_hex != expected_color:
            raise RuntimeError(f"StatusDot màu không khớp cho {status_key}")

    # False positive phải map về ignored
    dot.set_status("false_positive")
    internal_dot = getattr(dot, "_dot", None)
    if internal_dot is None or internal_dot.color_hex != STATUS_COLORS["ignored"]:
        raise RuntimeError("false_positive không map về ignored")


def test_score_bar() -> None:
    """Kiểm tra widget ScoreBar."""
    score_bar_widget = ScoreBar("security", score=80.0, weight=0.30)
    title_label = getattr(score_bar_widget, "_lbl_title", None)
    expected_title = TEN_TIEU_CHI["security"]
    if title_label is None or title_label.text() != expected_title:
        raise RuntimeError("ScoreBar tiêu đề không khớp TEN_TIEU_CHI")

    score_label = getattr(score_bar_widget, "_lbl_score", None)
    if score_label is None or score_label.text() != "80":
        raise RuntimeError("ScoreBar làm tròn điểm không đúng")

    # Cập nhật điểm không animation
    score_bar_widget.set_score(95.0, weight=0.25, animate=False)
    if score_label.text() != "95":
        raise RuntimeError("ScoreBar set_score thất bại")

    # Giới hạn cận 0-100
    score_bar_widget.set_score(150.0, animate=False)
    if score_bar_widget.score != 100.0:
        raise RuntimeError("ScoreBar không chặn cận trên 100")


def test_grade_label() -> None:
    """Kiểm tra widget GradeLabel."""
    grade_w = GradeLabel("A", 95.0)
    lbl_grade = getattr(grade_w, "_lbl_grade", None)
    lbl_score = getattr(grade_w, "_lbl_score", None)

    if lbl_grade is None or lbl_grade.text() != "A":
        raise RuntimeError("GradeLabel chữ cái xếp loại không đúng")
    if lbl_score is None or lbl_score.text() != "95 / 100":
        raise RuntimeError("GradeLabel điểm số không đúng")

    # Cập nhật điểm lẻ
    grade_w.set_grade_and_score("B", 82.6)
    if lbl_grade.text() != "B" or lbl_score.text() != "82.6 / 100":
        raise RuntimeError("GradeLabel set_grade_and_score thất bại")


def test_empty_state() -> None:
    """Kiểm tra widget EmptyState."""
    empty = EmptyState(
        title="Trống",
        description="Mô tả",
        action_text="Thêm",
    )
    title_lbl = getattr(empty, "_lbl_title", None)
    desc_lbl = getattr(empty, "_lbl_desc", None)
    btn_act = getattr(empty, "_btn_action", None)

    if title_lbl is None or title_lbl.text() != "Trống":
        raise RuntimeError("EmptyState tiêu đề không đúng")
    if desc_lbl is None or desc_lbl.text() != "Mô tả":
        raise RuntimeError("EmptyState mô tả không đúng")
    if btn_act is None or btn_act.text() != "Thêm" or btn_act.isHidden():
        raise RuntimeError("EmptyState nút bấm không hiển thị")

    # Kiểm tra phát tín hiệu
    clicked_fired = [False]

    def _on_clicked() -> None:
        clicked_fired[0] = True

    empty.action_clicked.connect(_on_clicked)
    btn_act.click()
    if not clicked_fired[0]:
        raise RuntimeError("EmptyState action_clicked signal không phát")

    # Ẩn nút khi action_text là None
    empty.set_action_text(None)
    if not btn_act.isHidden():
        raise RuntimeError("EmptyState nút bấm chưa bị ẩn")


def test_inline_notice() -> None:
    """Kiểm tra widget InlineNotice."""
    notice = InlineNotice(
        message="Lỗi kết nối",
        notice_type="error",
        action_text="Thử lại",
    )
    lbl_msg = getattr(notice, "_lbl_message", None)
    btn_act = getattr(notice, "_btn_action", None)

    if lbl_msg is None or lbl_msg.text() != "Lỗi kết nối":
        raise RuntimeError("InlineNotice thông điệp không đúng")
    if btn_act is None or btn_act.text() != "Thử lại":
        raise RuntimeError("InlineNotice nút bấm không đúng")

    # Kiểm tra phát cả 2 tín hiệu
    action_fired = [False]
    retry_fired = [False]

    def _on_action() -> None:
        action_fired[0] = True

    def _on_retry() -> None:
        retry_fired[0] = True

    notice.action_clicked.connect(_on_action)
    notice.retry_clicked.connect(_on_retry)
    btn_act.click()

    if not action_fired[0] or not retry_fired[0]:
        raise RuntimeError("InlineNotice signal không phát khi bấm")

    # Kiểm tra đổi type
    notice.set_notice_type("info")
    notice.set_message("Thông báo mới")
    if lbl_msg.text() != "Thông báo mới":
        raise RuntimeError("InlineNotice set_message thất bại")


def main() -> None:
    """Chạy toàn bộ bài kiểm thử đơn vị cho nhóm Widget."""
    print("Bắt đầu kiểm thử nhóm Widget dùng chung (Step 2)...", flush=True)
    test_severity_badge()
    print("  [x] SeverityBadge: OK", flush=True)
    test_status_dot()
    print("  [x] StatusDot: OK", flush=True)
    test_score_bar()
    print("  [x] ScoreBar: OK", flush=True)
    test_grade_label()
    print("  [x] GradeLabel: OK", flush=True)
    test_empty_state()
    print("  [x] EmptyState: OK", flush=True)
    test_inline_notice()
    print("  [x] InlineNotice: OK", flush=True)
    print("Toàn bộ 6 widget vượt qua 100% các tiêu chí kiểm thử!", flush=True)


if __name__ == "__main__":
    main()
