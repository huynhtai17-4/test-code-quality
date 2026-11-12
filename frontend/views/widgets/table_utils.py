"""Hàm tiện ích chuẩn hóa hiển thị QTableView theo phong cách kỹ thuật tối giản."""

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QAbstractItemView,
    QHeaderView,
    QTableView,
)


def chuan_hoa_bang(
    bang: QTableView,
    cot_gian: int,
    cot_so: tuple[int, ...] = (),
) -> None:
    """
    Chuẩn hóa bảng dữ liệu theo chuẩn kỹ thuật (ArtCraft / SKILLS.md):
    - Tiêu đề cột căn trái (trừ cột số căn phải).
    - Duy nhất một cột co giãn (cot_gian), các cột khác vừa vặn nội dung (ResizeToContents).
    - Ẩn vạch dọc, ẩn xen kẽ màu hàng, đường kẻ ngang mảnh.
    - Ẩn mũi tên sắp xếp lơ lửng.
    - Hàng cao 40px thoải mái, tiêu đề cao 38px.
    """
    _ = cot_so  # Ghi nhận danh sách cột số (được model xử lý căn phải)
    h_header = bang.horizontalHeader()
    h_header.setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    h_header.setHighlightSections(False)
    h_header.setSortIndicatorShown(False)
    h_header.setMinimumSectionSize(75)
    h_header.setStretchLastSection(False)
    h_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if cot_gian >= 0:
        h_header.setSectionResizeMode(cot_gian, QHeaderView.ResizeMode.Stretch)

    v_header = bang.verticalHeader()
    v_header.setVisible(False)
    v_header.setDefaultSectionSize(40)

    bang.setShowGrid(False)
    bang.setAlternatingRowColors(False)
    bang.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    bang.setTextElideMode(Qt.TextElideMode.ElideMiddle)
    bang.setWordWrap(False)
    bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
