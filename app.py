import os # ◀◀◀ 'os' 모듈을 임포트합니다.
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import re

# from dotenv import load_dotenv # .env는 더 이상 사용하지 않습니다.
# load_dotenv()

app = Flask(__name__)
CORS(app) 

# --- ◀◀◀ [핵심 변경] ---
# [중요] API 키를 코드에서 제거하고, '환경 변수'에서 읽어옵니다.
# Render 대시보드에서 'API_KEY'라는 이름으로 실제 키 값을 설정할 것입니다.
API_KEY = os.environ.get("API_KEY") 
# --- [변경 끝] ---

# API 키가 설정되지 않았을 경우를 대비한 방어 코드
if not API_KEY:
    print("="*50)
    print("경고: 'API_KEY' 환경 변수가 설정되지 않았습니다.")
    print("Render 또는 로컬 환경 변수에 API_KEY를 설정해야 합니다.")
    print("="*50)

# Gemini 2.5 Flash 모델 사용
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

# (이하 코드는 모두 동일합니다...)
# ... (기존 코드) ...
# ... (get_style_recommendation, get_personal_style, ...)
# ... (suggest_style, find_style, ...)

if __name__ == '__main__':
    # .env 파일 대신 Render의 환경 변수 PORT를 사용합니다.
    port = int(os.environ.get("PORT", 5001))
    
    # 0.0.0.0으로 실행해야 Render가 연결할 수 있습니다.
    # debug=True는 배포 환경에서 끄는 것이 좋지만, 
    # 지금은 테스트를 위해 켜두거나 app.run(host='0.0.0.0', port=port)로 해도 됩니다.
    app.run(debug=True, host='0.0.0.0', port=port)
