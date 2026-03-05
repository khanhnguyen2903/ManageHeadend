from django.shortcuts import render, redirect
from django.contrib import messages
from firebase_admin import db
from django.utils import timezone
from django.http import HttpResponse
import firebase_config

def add_user(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role')

        # Validate dữ liệu
        if not all([full_name, phone, password]):
            messages.error(request, "Vui lòng nhập đầy đủ thông tin.")
            return render(request, 'users/add_user.html')

        # Tạo user
        users_ref = db.reference('users')
        # Kiểm tra trùng user
        if users_ref.child(phone).get():
            messages.error(request, "Nhân viên đã tồn tại.")
            return render(request, 'users/add_user.html')
        
        users_ref.child(phone).set({
            'full_name': full_name,
            'phone': phone,
            'password': password,  # 👉 có thể hash nếu cần
            'role': role,
            'status': "Đang hoạt động",
            'created_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        messages.success(
            request,
            f"Đã thêm nhân viên {full_name} thành công."
        )
        return redirect('list_user')  # trang danh sách nhân viên

    return render(request, 'users/add_user.html')

def list_user(request):
    users_ref = db.reference('users')
    users_data = users_ref.get() or {}

    user_list = []

    for phone, info in users_data.items():
        user_list.append({
            'phone': phone,
            'full_name': info.get('full_name', ''),
            'role': info.get('role', 'staff'),
            'status': info.get('status', "Đang hoạt động"),
        })

    return render(request, 'users/list_user.html', {
        'users': user_list
    })

def edit_user(request, phone):
    users_ref = db.reference('users')
    user_ref = users_ref.child(phone)

    user_data = user_ref.get()
    user_data['is_staff'] = user_data.get('role') == 'staff'
    user_data['is_active'] = user_data.get('status') == 'Đang hoạt động'
    if not user_data:
        return HttpResponse("❌ Không tìm thấy nhân viên")
    
    # POST: CẬP NHẬT THÔNG TIN
    # ===============================
    if request.method == 'POST':
        full_name = request.POST.get('name')
        new_phone = request.POST.get('phone')
        password = request.POST.get('password')
        role = request.POST.get('role')
        status = request.POST.get('status')

        update_data = {
            'full_name': full_name,
            'phone': new_phone,
            'role': role,
            'status': status
        }

        # 🔐 Chỉ update mật khẩu khi có nhập
        if password:
            # update_data['password'] = hashlib.sha256(password.encode()).hexdigest()
            update_data['password'] = password
        
        # 🚀 Trường hợp đổi số điện thoại (đổi key)
        if new_phone != phone:
            # Tạo node mới
            users_ref.child(new_phone).set(update_data)

            # Xoá node cũ
            user_ref.delete()
        else:
            # Update trực tiếp
            user_ref.update(update_data)
        
        return redirect('list_user')
    
    return render(request, 'users/edit_user.html', {'user' : user_data})

def delete_user(request):
    pass

def login_user(request):
    if request.method == "POST":
        phone = request.POST.get("username")
        password = request.POST.get("password")

        if not phone or not password:
            messages.error(request, "Vui lòng nhập đầy đủ số điện thoại và mật khẩu")
            return render(request, "users/login.html")

        # 🔥 Lấy dữ liệu user theo phone (phone chính là key)
        user_ref = db.reference(f'users/{phone}')
        user_data = user_ref.get()

        if not user_data:
            messages.error(request, "Số điện thoại không tồn tại")
            return render(request, "users/login.html")

        # 🔐 So sánh mật khẩu
        if user_data.get("password") != password:
            messages.error(request, "Mật khẩu không chính xác")
            return render(request, "users/login.html")

        # ✅ Đăng nhập thành công → lưu session
        request.session["user_phone"] = phone
        request.session["user_name"] = user_data.get("full_name", "")
        # request.session["user_role"] = user_data.get("role", "")

        return redirect("shift_info")

    return render(request, "users/login.html")

def logout_user(request):
    request.session.flush()

    # Gửi message toast
    messages.success(request, "Đã đăng xuất thành công")

    # Chuyển về trang list_user
    return redirect('login_user')