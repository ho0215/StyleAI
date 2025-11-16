import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import re # ◀◀◀ JSON 파싱을 위한 정규표현식 모듈

app = Flask(__name__)
CORS(app)  # 모든 도메인에서의 요청을 허용합니다.

# --- [핵심] ---
# [중요] API 키를 코드에서 제거하고, '환경 변수'에서 읽어옵니다.
# Render 대시보드에서 'API_KEY'라는 이름으로 실제 키 값을 설정할 것입니다.
API_KEY = os.environ.get("API_KEY")
# --- [끝] ---

# API 키가 설정되지 않았을 경우를 대비한 방어 코드
if not API_KEY:
    print("="*50)
    print("경고: 'API_KEY' 환경 변수가 설정되지 않았습니다.")
    print("Render 또는 로컬 환경 변수에 API_KEY를 설정해야 합니다.")
    print("="*50)

# Gemini 2.5 Flash 모델 사용 (오타 수정됨)
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

# API 요청 헤더
headers = {
    "Content-Type": "application/json"
}

# -----------------------------------------------------------------
# [기능 1] 상황별 코디 - 스키마
# -----------------------------------------------------------------
recommendation_schema = {
    "type": "OBJECT",
    "properties": {
        "style_name": {"type": "STRING", "description": "스타일 이름 (예: 모던 캐주얼)"},
        "items": {
            "type": "ARRAY",
            "description": "패션 아이템 목록 (예: [\"흰색 옥스퍼드 셔츠\", \"네이비 슬랙스\"])",
            "items": {"type": "STRING"}
        }
    },
    "required": ["style_name", "items"]
}

gemini_schema = {
    "type": "OBJECT",
    "properties": {
        "recommendations": {
            "type": "ARRAY",
            "description": "3가지 패션 추천 조합",
            "items": recommendation_schema
        }
    },
    "required": ["recommendations"]
}

# -----------------------------------------------------------------
# [기능 2] 스타일 찾기 - 스키마
# -----------------------------------------------------------------
style_finder_schema = {
    "type": "OBJECT",
    "properties": {
        "style_name": {"type": "STRING", "description": "사용자에게 어울리는 스타일 이름 (예: 스트릿 캐주얼, 미니멀리즘)"},
        "description": {"type": "STRING", "description": "해당 스타일에 대한 2-3문장의 간결한 설명"}
    },
    "required": ["style_name", "description"]
}


# -----------------------------------------------------------------
# [기능 1] Gemini API 호출 함수
# -----------------------------------------------------------------
def get_style_recommendation(situation):
    """
    Google Gemini API를 호출하여 스타일 추천을 받는 함수
    """
    system_prompt = f"""
    당신은 세계 최고의 패션 스타일리스트입니다. 
    사용자가 제시한 특정 상황에 맞는 3가지 패션 아이템 조합(상의, 하의, 아우터, 신발, 액세서리 등)을 제안해야 합니다.
    
    반드시 {gemini_schema} JSON 스키마 형식으로 응답해야 합니다.
    """
    
    user_prompt = f"'{situation}' 상황에 어울리는 3가지 스타일을 제안해주세요."

    payload = {
        "contents": [
            {"parts": [{"text": user_prompt}]}
        ],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema,
            "temperature": 0.7,
            "maxOutputTokens": 2048 # ◀◀◀ 토큰 수를 2048로 늘림
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외를 발생시킵니다.
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None

# -----------------------------------------------------------------
# [기능 2] Gemini API 호출 함수
# -----------------------------------------------------------------
def get_personal_style(q1_clothes, q2_colors, q3_places):
    """
    Google Gemini API를 호출하여 개인 스타일을 분석하는 함수
    """
    system_prompt = f"""
    당신은 사용자의 패션 취향을 분석하는 스타일 큐레이터입니다.
    사용자의 답변을 바탕으로, 그 사람의 핵심 스타일 1가지를 정의해야 합니다.
    
    반드시 {style_finder_schema} JSON 스키마 형식으로 응답해야 합니다.
    """
    
    user_prompt = f"""
    사용자의 패션 취향입니다:
    - 즐겨 입는 옷: {q1_clothes}
    - 선호하는 색상: {q2_colors}
    - 자주 가는 장소: {q3_places}
    
    이 정보를 바탕으로 사용자의 스타일 이름과 간단한 설명을 1가지만 제안해주세요.
    """

    payload = {
        "contents": [
            {"parts": [{"text": user_prompt}]}
        ],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": style_finder_schema,
            "temperature": 0.5,
            "maxOutputTokens": 1024 # ◀◀◀ 토큰 수를 1024로 늘림
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None


# -----------------------------------------------------------------
# 루트 엔드포인트
# -----------------------------------------------------------------
@app.route('/')
def home():
    return "Flask-based StyleAI (v_deploy) 백엔드 서버가 실행 중입니다."

# -----------------------------------------------------------------
# [기능 1] 상황별 코디 추천 엔드포인트
# -----------------------------------------------------------------
@app.route('/api/suggest-style', methods=['POST'])
def suggest_style():
    data = request.json
    situation = data.get('situation', '가벼운 산책')
    
    api_response = get_style_recommendation(situation) 

    if api_response and 'candidates' in api_response:
        try:
            # ◀◀◀ [강화된 파싱 로직 1] ---
            candidate = api_response['candidates'][0]
            
            # 응답이 정상적으로 완료되었는지 확인
            if 'finishReason' in candidate and candidate['finishReason'] != 'STOP':
                raise Exception(f"API 응답이 비정상적으로 종료되었습니다: {candidate['finishReason']}")

            part = candidate['content']['parts'][0]
            json_object = None

            # 1. Gemini가 JSON 객체를 바로 반환한 경우 (가장 좋은 시나리오)
            if 'json' in part: 
                json_object = part['json']
            elif 'object' in part:
                json_object = part['object']

            # 2. Gemini가 'text' 필드에 JSON 문자열을 반환한 경우 (파싱 필요)
            elif 'text' in part:
                raw_text = part['text']
                
                # 3. 마크다운(` ```json ... ``` `)이나 불필요한 텍스트를 제거하기 위해
                #    첫 '{'와 마지막 '}' 사이의 내용만 추출합니다.
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                
                if match:
                    json_string = match.group(0)
                    json_object = json.loads(json_string) # ◀◀◀ 추출된 JSON 문자열 파싱
                else:
                    # 텍스트에서 JSON 블록을 찾지 못한 경우
                    raise Exception(f"응답 텍스트에서 JSON 객체를 찾지 못했습니다. Gemini가 반환한 텍스트: '{raw_text}'")
            
            # 4. 객체를 성공적으로 찾았는지 확인합니다.
            if json_object:
                return jsonify(json_object)
            else:
                raise KeyError("Gemini 응답에서 'text', 'json', 또는 'object' 필드를 찾을 수 없습니다.")
            # --- [파싱 로직 끝] ---
            
        except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
            error_message = f"API 응답 파싱 중 오류: {e}"
            print(error_message)
            print(f"전체 API 응답: {api_response}")
            return jsonify({"error": error_message}), 500
    else:
        print(f"API로부터 응답을 받지 못했거나 'candidates'가 없습니다: {api_response}")
        return jsonify({"error": "Gemini API로부터 응답을 받지 못했습니다."}), 500

# -----------------------------------------------------------------
# [기능 2] 나의 스타일 찾기 엔드포인트
# -----------------------------------------------------------------
@app.route('/api/find-style', methods=['POST'])
def find_style():
    data = request.json
    q1 = data.get('q1_clothes', '알 수 없음')
    q2 = data.get('q2_colors', '알 수 없음')
    q3 = data.get('q3_places', '알 수 없음')
    
    api_response = get_personal_style(q1, q2, q3)

    if api_response and 'candidates' in api_response:
        try:
            # ◀◀◀ [강화된 파싱 로직 2] (suggest_style과 동일) ---
            candidate = api_response['candidates'][0]
            
            if 'finishReason' in candidate and candidate['finishReason'] != 'STOP':
                raise Exception(f"API 응답이 비정상적으로 종료되었습니다: {candidate['finishReason']}")

            part = candidate['content']['parts'][0]
            json_object = None

            if 'json' in part: 
                json_object = part['json']
            elif 'object' in part:
                json_object = part['object']
            elif 'text' in part:
                raw_text = part['text']
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                
                if match:
                    json_string = match.group(0)
                    json_object = json.loads(json_string)
                else:
                    raise Exception(f"응답 텍스트에서 JSON 객체를 찾지 못했습니다. Gemini가 반환한 텍스트: '{raw_text}'")
            
            if json_object:
                return jsonify(json_object)
            else:
                raise KeyError("Gemini 응답에서 'text', 'json', 또는 'object' 필드를 찾을 수 없습니다.")
            # --- [파싱 로직 끝] ---
            
        except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
            error_message = f"API 응답 파싱 중 오류: {e}"
            print(error_message)
            print(f"전체 API 응답: {api_response}")
            return jsonify({"error": error_message}), 500
    else:
        print(f"API로부터 응답을 받지 못했거나 'candidates'가 없습니다: {api_response}")
        return jsonify({"error": "Gemini API로부터 응답을 받지 못했습니다."}), 500

# -----------------------------------------------------------------
# 앱 실행
# -----------------------------------------------------------------
if __name__ == '__main__':
    # .env 파일 대신 Render의 환경 변수 PORT를 사용합니다.
    # Render는 10000번 포트를 기본으로 사용합니다.
    port = int(os.environ.get("PORT", 10000))
    
    # 0.0.0.0으로 실행해야 Render가 연결할 수 있습니다.
    # 배포 환경에서는 debug=False가 권장됩니다.
    app.run(debug=False, host='0.0.0.0', port=port)
