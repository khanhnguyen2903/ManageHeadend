import firebase_admin
from firebase_admin import credentials, db
import os, json
from django.conf import settings

# Kiểm tra biến môi trường
firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS')
if firebase_creds_json:
    # Chạy trên Render: dùng biến môi trường
    cred = credentials.Certificate(json.loads(firebase_creds_json))
else:
    # Chạy local: dùng file JSON
    # Đường dẫn tuyệt đối tới file firebase_config.json
    firebaseKey_path = os.path.join(settings.BASE_DIR, 'firebase_key.json')
    # Load credentials từ file JSON
    cred = credentials.Certificate(firebaseKey_path)
# Tránh khởi tạo lại Firebase nhiều lần
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://manageheadend-default-rtdb.firebaseio.com/'  # thay bằng URL thật của bạn
    })