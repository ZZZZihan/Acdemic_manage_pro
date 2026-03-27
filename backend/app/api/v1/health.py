from flask import jsonify

from app.api.v1 import api


@api.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'backend-v1',
    }), 200
