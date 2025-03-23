from flask import jsonify
from app.api.v1 import api

def bad_request(message):
    response = jsonify({'error': 'bad request', 'message': message})
    response.status_code = 400
    return response

def unauthorized(message):
    response = jsonify({'error': 'unauthorized', 'message': message})
    response.status_code = 401
    return response

def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response.status_code = 403
    return response

def not_found(message):
    response = jsonify({'error': 'not found', 'message': message})
    response.status_code = 404
    return response

@api.app_errorhandler(404)
def page_not_found(e):
    return not_found('资源不存在')

@api.app_errorhandler(500)
def internal_server_error(e):
    response = jsonify({'error': 'internal server error', 'message': '服务器内部错误'})
    response.status_code = 500
    return response 