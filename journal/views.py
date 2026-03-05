from django.shortcuts import render, redirect
from django.utils import timezone
from firebase_admin import db
from datetime import datetime
from django.contrib import messages
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings
from collections import OrderedDict

def shift_info(request):
    user_name = request.session.get("user_name")

    if not user_name:
        redirect("login_user")

    if request.method == "POST":
        # 📥 Lấy dữ liệu từ form
        location = request.POST.get("location")
        shift = request.POST.get("shift")

        # 🧠 Lưu vào session
        request.session["shift_location"] = location
        request.session["shift_time"] = shift

        # (khuyến nghị) Đánh dấu session đã được chỉnh sửa
        request.session.modified = True

        # 👉 Chuyển sang trang thêm nhật ký
        return redirect("list_journal")

    # GET request
    return render(request, "journal/shift_info.html", {"name": user_name})


def add_journal(request):
    user_name = request.session.get("user_name")
    shift_location = request.session.get("shift_location")
    shift_time = request.session.get("shift_time")

    if not shift_location:
        return redirect("shift_info")

    if not shift_time:
        return redirect("shift_info")

    if request.method == "POST":
        # 📥 Lấy dữ liệu từ form
        content = request.POST.get("content")
        job_type = request.POST.get("job_type")
        status = request.POST.get("status")
        incident_reason = request.POST.get("incident_reason", "")

        # ⏰ Thời gian tạo (ISO để dễ sort & đọc)
        created_at = timezone.now().isoformat()

        # 🧱 Chuẩn bị data lưu Firebase
        journal_data = {
            "content": content,
            "job_type": job_type,
            "status": status,
            "created_by": user_name,
            "created_at": created_at,
            "shift_location": shift_location,
            "shift_time": shift_time,
        }

        # 🚨 Chỉ lưu nguyên nhân nếu là sự cố
        if job_type == "Sự cố":
            journal_data["incident_reason"] = incident_reason

        # 🔥 Lưu vào Firebase Realtime Database
        journals_ref = db.reference("journals")
        journals_ref.push(journal_data)

        # ✅ Sau khi lưu xong → quay lại trang add hoặc trang danh sách
        return redirect("list_journal")  # hoặc redirect("list_journal")

    # GET request
    return render(
        request,
        "journal/add_journal.html",
        {"name": user_name, "shift_location": shift_location, "shift_time": shift_time},
    )


def list_journal(request):
    # 🔐 (khuyến nghị) kiểm tra đăng nhập
    user_name = request.session.get("user_name")
    if not user_name:
        return redirect("login")

    # 🔥 Lấy dữ liệu từ Firebase
    journals_ref = db.reference("journals")
    journals_data = journals_ref.get()

    journals = []

    if journals_data:
        for key, value in journals_data.items():
            journal = {
                "key": key,
                "content": value.get("content", ""),
                "job_type": value.get("job_type", ""),
                "status": value.get("status", ""),
                "incident_reason": value.get("incident_reason", ""),
                "created_by": value.get("created_by", ""),
                "created_at": value.get("created_at", ""),
                # thông tin ca trực
                "shift_location": value.get("shift_location", ""),
                "shift_time": value.get("shift_time", ""),
            }

            # 📅 Format ngày trực từ created_at
            if journal["created_at"]:
                try:
                    dt = datetime.fromisoformat(journal["created_at"])
                    journal["date"] = dt.strftime("%d/%m/%Y")
                except Exception:
                    journal["date"] = journal["created_at"]
            else:
                journal["date"] = ""

            journals.append(journal)

    # 🔃 Sắp xếp mới nhất → cũ nhất
    journals.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return render(request, "journal/list_journal.html", {"journals": journals})


def edit_journal(request, key):
    # 🔒 Kiểm tra đăng nhập
    user_name = request.session.get("user_name")

    if not user_name:
        redirect("login_user")

    shift_location = request.session.get("shift_location")
    shift_time = request.session.get("shift_time")

    journal_ref = db.reference(f"journals/{key}")

    # Danh sách loại công việc (CHUẨN HÓA 1 NƠI)
    JOB_TYPES = [
        ("Sự cố", "🚨 Sự cố"),
        ("Kiểm tra kênh TH", "📺 Kiểm tra kênh TH"),
        ("Cập nhật bảng kênh", "🗂️ Cập nhật bảng kênh"),
        ("Khác", "🔧 Khác"),
    ]

    # =========================
    # GET: hiển thị dữ liệu cũ
    # =========================
    if request.method == "GET":
        journal = journal_ref.get()

        if not journal:
            messages.error(request, "❌ Nhật ký không tồn tại")
            return redirect("list_journal")

        context = {
            "name": user_name,
            "shift_location": shift_location,
            "shift_time": shift_time,
            "journal": journal,
            "job_types": JOB_TYPES,  # 👈 truyền xuống template
        }
        return render(request, "journal/edit_journal.html", context)

    # =========================
    # POST: cập nhật dữ liệu
    # =========================
    if request.method == "POST":
        content = request.POST.get("content")
        job_type = request.POST.get("job_type")
        incident_reason = request.POST.get("incident_reason", "")
        status = request.POST.get("status")

        # Nếu là sự cố thì update cả incident_reason
        if job_type == "Sự cố":
            journal_ref.update(
                {
                    "content": content,
                    "job_type": job_type,
                    "incident_reason": incident_reason,
                    "status": status,
                }
            )
        else:
            journal_ref.update(
                {
                    "content": content,
                    "job_type": job_type,
                    "status": status,
                }
            )
        # ✅ Alert thành công
        messages.success(request, "✅ Cập nhật nhật ký công việc thành công!")

        return redirect("list_journal")


def delete_journal(request, key):
    # 🔒 Kiểm tra đăng nhập
    user_name = request.session.get("user_name")
    if not user_name:
        return redirect("login_user")

    shift_location = request.session.get("shift_location")
    shift_time = request.session.get("shift_time")

    journal_ref = db.reference(f"journals/{key}")
    journal = journal_ref.get()

    # ❌ Không tồn tại
    if not journal:
        messages.error(request, "❌ Công việc không tồn tại hoặc đã bị xoá")
        return redirect("list_journal")

    # 🔒 Kiểm tra quyền xoá
    if (
        journal.get("created_by") != user_name
        or journal.get("shift_location") != shift_location
        or journal.get("shift_time") != shift_time
    ):
        messages.error(
            request,
            "⛔ Bạn không có quyền xoá công việc này (không phải do bạn tạo hoặc khác ca trực)",
        )
        return redirect("list_journal")

    # ✅ Đủ quyền → xoá
    journal_ref.delete()
    messages.success(request, "🗑️ Đã xoá công việc thành công!")

    return redirect("list_journal")


def export_journal_pdf(request):
    # 🔐 Kiểm tra đăng nhập
    user_name = request.session.get("user_name")
    if not user_name:
        return redirect("login")

    # 📥 Nhận khoảng ngày từ query string
    start = request.GET.get("start")  # YYYY-MM-DD
    end = request.GET.get("end")  # YYYY-MM-DD

    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None

    # 🔥 Lấy dữ liệu từ Firebase
    journals_ref = db.reference("journals")
    journals_data = journals_ref.get()

    journals = []

    if journals_data:
        for key, value in journals_data.items():
            created_at = value.get("created_at", "")
            if not created_at:
                continue

            try:
                dt = datetime.fromisoformat(created_at)
                journal_date = dt.date()
            except Exception:
                continue

            # 🎯 Lọc theo khoảng ngày
            if start_date and journal_date < start_date:
                continue
            if end_date and journal_date > end_date:
                continue

            journals.append(
                {
                    "date_obj": journal_date,
                    "date": journal_date.strftime("%d/%m/%Y"),
                    "shift_time": value.get("shift_time", ""),
                    "shift_location": value.get("shift_location", ""),
                    "created_by": value.get("created_by", ""),
                    "content": value.get("content", ""),
                    "job_type": value.get("job_type", ""),
                    "status": value.get("status", ""),
                }
            )

    # ================== 🔃 Sắp xếp ==================
    journals.sort(
        key=lambda x: (
            x["date_obj"],
            x["shift_time"],
            x["shift_location"],
            x["created_by"],
        )
    )
    # ================== 📌 Gộp theo (Ngày + Ca + Headend + Nhân viên) ==================
    grouped = OrderedDict()

    for j in journals:
        group_key = (
            j["date"],
            j["shift_time"],
            j["shift_location"],
            j["created_by"],
        )

        if group_key not in grouped:
            grouped[group_key] = {
                "date": j["date"],
                "shift_time": j["shift_time"],
                "shift_location": j["shift_location"],
                "created_by": j["created_by"],
                "content": [],
                "job_type": [],
                "status": [],
            }

        grouped[group_key]["content"].append(j["content"])
        grouped[group_key]["job_type"].append(j["job_type"])
        grouped[group_key]["status"].append(j["status"])

    # ================= PDF =================
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="bao_cao_nhat_ky_ca_truc.pdf"'
    )
    # ================== Font Times New Roman ==================
    FONT_DIR = os.path.join(settings.BASE_DIR, "journal", "fonts")

    pdfmetrics.registerFont(TTFont("TNR", os.path.join(FONT_DIR, "times.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-Bold", os.path.join(FONT_DIR, "timesbd.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-Italic", os.path.join(FONT_DIR, "timesi.ttf")))
    pdfmetrics.registerFont(
        TTFont("TNR-BoldItalic", os.path.join(FONT_DIR, "timesbi.ttf"))
    )
    # ================== PDF Document ==================
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )
    # ===== Styles dùng font Unicode =====
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = "TNR"
    styles["Title"].fontName = "TNR-Bold"

    header_style = ParagraphStyle(
        "HeaderStyle",
        parent=styles["Normal"],
        fontName="TNR-Bold",
        fontSize=9,
        alignment=1,
    )

    cell_style = ParagraphStyle(
        "CellStyle",
        parent=styles["Normal"],
        fontName="TNR",
        fontSize=9,
    )

    elements = []

    # ===== Tiêu đề =====
    elements.append(
        Paragraph("<b>BÁO CÁO NHẬT KÝ CA TRỰC HEADEND</b>", styles["Title"])
    )

    # Format lại ngày hiển thị
    try:
        start_display = (
            datetime.strptime(start, "%Y-%m-%d").strftime("%d/%m/%Y")
            if start
            else "---"
        )
    except Exception:
        start_display = "---"

    try:
        end_display = (
            datetime.strptime(end, "%Y-%m-%d").strftime("%d/%m/%Y") if end else "---"
        )
    except Exception:
        end_display = "---"

    subtitle = f"Từ ngày {start_display} đến {end_display}"

    elements.append(Paragraph(subtitle, styles["Normal"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    def join_with_separator(items):
        if not items:
            return ""
        if len(items) == 1:
            return items[0]

        return "<br/><hr width='100%' color='#000000'/><br/>".join(items)

    # ===== Bảng dữ liệu =====
    data = [
        [
            Paragraph("Ngày trực", header_style),
            Paragraph("Ca trực", header_style),
            Paragraph("Headend", header_style),
            Paragraph("Nhân viên", header_style),
            Paragraph("Nội dung", header_style),
            Paragraph("Loại công việc", header_style),
            Paragraph("Trạng thái", header_style),
        ]
    ]

    for g in grouped.values():
        data.append(
            [
                Paragraph(g["date"], cell_style),
                Paragraph(g["shift_time"], cell_style),
                Paragraph(g["shift_location"], cell_style),
                Paragraph(g["created_by"], cell_style),
                Paragraph(join_with_separator(g["content"]), cell_style),
                Paragraph(join_with_separator(g["job_type"]), cell_style),
                Paragraph(join_with_separator(g["status"]), cell_style),
            ]
        )
    # ================== Merge ô Ngày trực và ô ca trực trùng nhau ==================
    merge_commands = []

    group_values = list(grouped.values())

    # ===== Merge Ngày (cột 0) =====
    current_date = None

    start_row_date = 1

    for i in range(1, len(data)):
        row = group_values[i - 1]
        row_date = row["date"]

        if current_date is None:
            current_date = row_date
            start_row_date = i

        elif row_date != current_date:
            if i - start_row_date > 1:
                merge_commands.append(("SPAN", (0, start_row_date), (0, i - 1)))
            current_date = row_date
            start_row_date = i

    # nhóm cuối
    if len(data) - start_row_date > 1:
        merge_commands.append(("SPAN", (0, start_row_date), (0, len(data) - 1)))

    # ===== Merge Ca (cột 1) =====
    current_date = None
    current_shift = None
    start_row = 1  # bắt đầu từ row 1 vì row 0 là header

    for i in range(1, len(data)):
        row = group_values[i - 1]
        row_date = row["date"]
        row_shift = row["shift_time"]

        if current_date is None:
            current_date = row_date
            current_shift = row_shift
            start_row = i

        elif row_date != current_date or row_shift != current_shift:
            # Nếu có nhiều hơn 1 dòng thì merge
            if i - start_row > 1:
                merge_commands.append(("SPAN", (1, start_row), (1, i - 1)))

            current_date = row_date
            current_shift = row_shift
            start_row = i

    # Xử lý nhóm cuối cùng
    if len(data) - start_row > 1:
        merge_commands.append(("SPAN", (1, start_row), (1, len(data) - 1)))

    table = Table(data, repeatRows=1, colWidths=[70, 70, 90, 90, 260, 100, 80])
    table_style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]
    # Thêm các lệnh merge
    table_style.extend(merge_commands)

    table.setStyle(TableStyle(table_style))

    elements.append(table)
    doc.build(elements)

    return response
