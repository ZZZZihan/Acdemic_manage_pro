import os

import uvicorn

from app_v2.main import create_app


app = create_app(database_url=os.environ.get('V2_DATABASE_URL'))


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('V2_PORT', '8003')))
