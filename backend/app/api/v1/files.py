import os
import uuid
import datetime
from flask import request, send_from_directory, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.api.v1 import api
from app.models import User
import logging

# 允许的文件类型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png'}
# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# 检查文件是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 获取上传路径
def get_upload_path():
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return upload_folder

@api.route('/files/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """
    上传文件API
    支持多文件上传
    """
    current_user_id = get_jwt_identity()
    
    logging.info(f"文件上传请求: {request.files}")
    logging.info(f"表单数据: {request.form}")
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    # 检查用户是否存在
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"msg": "用户不存在"}), 404
    
    # 检查是否有文件
    if 'file' not in request.files:
        return jsonify({"msg": "没有文件"}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"msg": "没有文件"}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({"msg": f"不支持的文件类型，允许的类型: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
    
    # 记录文件信息
    logging.info(f"文件名: {file.filename}, 内容类型: {file.content_type}")
    
    # 检查文件大小
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    logging.info(f"文件大小: {file_size} 字节")
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({"msg": f"文件大小超过限制 (最大 {MAX_FILE_SIZE/1024/1024}MB)"}), 400
    
    # 生成安全的文件名
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = str(uuid.uuid4().hex)[:8]
    filename = f"{timestamp}_{unique_id}.{file.filename.rsplit('.', 1)[1].lower()}"
    
    # 保存文件
    upload_folder = get_upload_path()
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    # 返回文件信息
    return jsonify({
        'msg': '文件上传成功',
        'file_path': filename,
        'original_name': file.filename
    }), 200

@api.route('/files/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    下载文件API
    """
    upload_folder = get_upload_path()
    original_name = request.args.get('original_name', filename)
    return send_from_directory(upload_folder, filename, as_attachment=True, download_name=original_name) 