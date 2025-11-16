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
API_URL = f"https://generativelanguges.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

# API 요청 헤더
headers = {
    "Content-Type": "application/json"
}

# -----------------------------------------------------------------
# [기능 1] 상황별 코디 추천 스키마
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
# [기능 2 - 신규] 나의 스타일 찾기 스키마
# -----------------------------------------------------------------
style_finder_schema = {
    "type": "OBJECT",
    "properties": {
        "style_name": {
            "type": "STRING", 
            "description": "분석된 스타일 이름 (예: '미니멀리즘', '스트릿 캐주얼')"
        },
        "description": {
            "type": "STRING", 
            "description": "왜 그렇게 분석했는지에 대한 1~2줄의 간결한 설명"
        }
    },
    "required": ["style_name", "description"]
}

# -----------------------------------------------------------------
# [기능 1] 상황별 코디 추천 함수
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
            "maxOutputTokens": 2048 # ◀◀◀ 1000에서 2048로 늘림
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
# [기능 2 - 신규] 나의 스타일 찾기 함수
# -----------------------------------------------------------------
def get_personal_style(q1_clothes, q2_colors, q3_places):
    """
    Google Gemini API를 호출하여 개인 스타일을 분석하는 함수
    """
    system_prompt = f"""
    당신은 사용자의 취향을 분석하여 패션 스타일을 정의해주는 전문 패션 컨설턴트입니다.
    사용자의 답변을 기반으로, 그 사람의 핵심 스타일을 1~2 단어의 '스타일 이름'으로 정의하고, 
    왜 그렇게 생각했는지 '설명'을 덧붙여야 합니다.
    
    반드시 {style_finder_schema} JSON 스키마 형식으로 응답해야 합니다.
    """
    
    user_prompt = f"""
    다음은 사용자의 패션 취향입니다:
    - 즐겨 입는 옷: {q1_clothes}
    - 선호하는 색상: {q2_colors}
    - 자주 가는 장소: {q3_places}
    
    이 사람의 패션 스타일을 분석해주세요.
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
            "responseSchema": style_finder_schema, # ◀◀◀ 다른 스키마 사용
            "temperature": 0.5,
            "maxOutputTokens": 1024 # ◀◀◀ 500에서 1024로 늘림
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None


# --- API 엔드포인트 ---

@app.route('/')
def home():
    return "Flask-based StyleAI (Simple v, Gemini) 백엔드 서버가 실행 중입니다. (v2)"

# [기능 1] 상황별 코디 추천 엔드포인트
@app.route('/api/suggest-style', methods=['POST'])
def suggest_style():
    data = request.json
    situation = data.get('situation', '가벼운 산책')
    api_response = get_style_recommendation(situation) 

    if api_response and 'candidates' in api_response:
        try:
            # --- ◀◀◀ [핵심 변경] ---
            candidate = api_response['candidates'][0]
            
            # 1. Gemini가 응답을 완료했는지 확인합니다.
            finish_reason = candidate.get('finishReason')
            if finish_reason and finish_reason != 'STOP':
                # 'MAX_TOKENS', 'SAFETY' 등의 이유로 중단된 경우
                # (이제 'MAX_TOKENS'가 오류의 원인이었음을 알 수 있습니다)
                raise Exception(f"Gemini가 응답을 중단했습니다. (이유: {finish_reason})")

            # 2. 응답 내용(part)을 가져옵니다.
            if 'content' not in candidate or 'parts' not in candidate['content']:
                raise KeyError("API 응답에 'content' 또는 'parts'가 없습니다.")
                
            part = candidate['content']['parts'][0]
            json_object = None

            # 3. Gemini가 JSON 객체를 바로 반환한 경우 (가장 좋은 시나리오)
            if 'json' in part: 
                json_object = part['json']
            elif 'object' in part:
                json_object = part['object']

            # 4. Gemini가 'text' 필드에 JSON 문자열을 반환한 경우 (파싱 필요)
            elif 'text' in part:
                raw_text = part['text']
                
                # 5. 마크다운(` ```json ... ``` `)이나 불필요한 텍스트를 제거하기 위해
                #    첫 '{'와 마지막 '}' 사이의 내용만 추출합니다.
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                
                if match:
                    json_string = match.group(0)
                    json_object = json.loads(json_string) # ◀◀◀ 추출된 JSON 문자열 파싱
                else:
                    # 텍스트에서 JSON 블록을 찾지 못한 경우
                    raise Exception(f"응답 텍스트에서 JSON 객체를 찾지 못했습니다. Gemini가 반환한 텍스트: '{raw_text}'")
            
            # 6. 객체를 성공적으로 찾았는지 확인합니다.
            if json_object:
                return jsonify(json_object)
            else:
                raise KeyError("Gemini 응답에서 'text', 'json', 또는 'object' 필드를 찾을 수 없습니다.")
            # --- [변경 끝] ---
            
        except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
            error_message = f"API 응답 파싱 중 오류: {str(e)}"
            print(error_message)
            print(f"전체 API 응답: {api_response}") 
            return jsonify({"error": error_message}), 500
    else:
        print(f"API로부터 응답을 받지 못했거나 'candidates'가 없습니다: {api_response}")
        return jsonify({"error": "Gemini API로부터 응답을 받지 못했습니다."}), 500

# -----------------------------------------------------------------
# [기능 2 - 신규] 나의 스타일 찾기 엔드포인트
# -----------------------------------------------------------------
@app.route('/api/find-style', methods=['POST'])
def find_style():
    data = request.json
    
    q1 = data.get('q1_clothes', '청바지와 티셔츠')
    q2 = data.get('q2_colors', '무채색')
    q3 = data.get('q3_places', '카페, 학교')

    api_response = get_personal_style(q1, q2, q3)

    if api_response and 'candidates' in api_response:
        try:
            # (파싱 로직은 suggest_style과 동일하게 수정)
            # --- ◀◀◀ [핵심 변경] ---
            candidate = api_response['candidates'][0]
            
            # 1. Gemini가 응답을 완료했는지 확인합니다.
            finish_reason = candidate.get('finishReason')
            if finish_reason and finish_reason != 'STOP':
                # 'MAX_TOKENS', 'SAFETY' 등의 이유로 중단된 경우
                raise Exception(f"Gemini가 응답을 중단했습니다. (이유: {finish_reason})")

            # 2. 응답 내용(part)을 가져옵니다.
            if 'content' not in candidate or 'parts' not in candidate['content']:
                raise KeyError("API 응답에 'content' 또는 'parts'가 없습니다.")
                
            part = candidate['content']['parts'][0]
            json_object = None

            # 3. Gemini가 JSON 객체를 바로 반환한 경우
            if 'json' in part: 
                json_object = part['json']
            elif 'object' in part:
                json_object = part['object']

            # 4. Gemini가 'text' 필드에 JSON 문자열을 반환한 경우
            elif 'text' in part:
                raw_text = part['text']
                
                # 5. 첫 '{'와 마지막 '}' 사이의 내용만 추출
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                
                if match:
                    json_string = match.group(0)
                    json_object = json.loads(json_string) # ◀◀◀ 추출된 JSON 문자열 파싱
                else:
                    raise Exception(f"응답 텍스트에서 JSON 객체를 찾지 못했습니다. Gemini가 반환한 텍스트: '{raw_text}'")
            
            # 6. 객체를 성공적으로 찾았는지 확인합니다.
            if json_object:
                return jsonify(json_object)
            else:
                raise KeyError("Gemini 응답에서 'text', 'json', 또는 'object' 필드를 찾을 수 없습니다.")
            # --- [변경 끝] ---
            
        except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
            error_message = f"API 응답 파싱 중 오류: {str(e)}"
            print(error_message)
            print(f"전체 API 응답: {api_response}") 
            return jsonify({"error": error_message}), 500
    else:
        print(f"API로부터 응답을 받지 못했거나 'candidates'가 없습니다: {api_response}")
        return jsonify({"error": "Gemini API로부터 응답을 받지 못했습니다."}), 500


if __name__ == '__main__':
    # .env 파일 대신 Render의 환경 변수 PORT를 사용합니다.
    port = int(os.environ.get("PORT", 5001))
    
    # 0.0.0.0으로 실행해야 Render가 연결할 수 있습니다.
    # debug=True는 배포 환경에서 끄는 것이 좋지만, 
    # 지금은 테스트를 위해 켜두거나 app.run(host='0.0.0.0', port=port)로 해도 됩니다.
    app.run(debug=True, host='0.0.0.0', port=port)