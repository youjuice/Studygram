from bson import ObjectId
from flask import Flask, render_template, request, jsonify,redirect,session
from flask_cors import CORS
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity, get_jwt
from flask.json.provider import JSONProvider
import json
import jwt
from pymongo import MongoClient
import bcrypt
import requests
from datetime import timedelta
from init_db import add_workbook_db, add_study_db

app = Flask(__name__)
CORS(app)

# for local
# client = MongoClient('localhost', 27017)

# for live
client = MongoClient('mongodb://test:test@15.165.214.88', 27017)

db = client.studygram

app.config["JWT_SECRET_KEY"] = "super-secret"
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
jwt = JWTManager(app)

collection = db['study']

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

class CustomJSONProvider(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, **kwargs, cls=CustomJSONEncoder)
    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)
    
app.json = CustomJSONProvider(app)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login')
def hello_world():
    return render_template('login.html')

@app.route('/index')
def test():
    return render_template('index.html')

# API #2: 로그인 기능 구현
@app.route('/login', methods=['POST'])
def login():
    username = request.form['usernames']
    password = request.form['passwords']

    # 사용자 이름을 기반으로 사용자 정보를 데이터베이스에서 가져옵니다.
    user = db.userInfo.find_one({'username': username})

    if user is not None and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        backjoonid = user["backjoonId"]
        # 비밀번호가 일치하는 경우 JWT 생성 및 반환
        access_token = create_access_token(identity=username, additional_claims={"backjoonId":backjoonid})
        return jsonify({"result": "success", "access_token": access_token, "baekjoonId" : backjoonid}), 200
    elif user is None:
        return jsonify({"msg": "없는 아이디 입니다."}), 461

    else:
        # 비밀번호가 일치하지 않는 경우
        return jsonify({"msg": "비밀번호가 틀립니다"}), 462
    

# # API #2-2: JWT 인증을 요구하는 라우트 보호
# @app.route('/protected', methods=['GET'])
# @jwt_required()
# def protected():
#     current_user = get_jwt_identity()
#     return jsonify(logged_in_as=current_user), 200

# API #2-3 : 회원가입
@app.route('/register', methods=['POST'])
def register():
    r_username = request.form['give_username']
    r_password = request.form['give_password']
    r_baekjoonId = request.form['give_baekjoonId']

    url = "https://www.acmicpc.net/user/" + r_baekjoonId

    session_obj = requests.Session()
    response = session_obj.get(url, headers = {"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        return jsonify({"error": "백준에 없는 사용자입니다."}), 471
    
    existing_user = db.userInfo.find_one({'username': r_username})

    if existing_user:
        return jsonify({"error": "이미 존재하는 사용자입니다"}), 472
    
    existing_baekjoonId = db.userInfo.find_one({'backjoonId': r_baekjoonId})

    if existing_baekjoonId:
        return jsonify({"error": "이미 존재하는 백준 사용자입니다"}), 473
    
    hashed_password = bcrypt.hashpw(r_password.encode('utf-8'), bcrypt.gensalt())
    data = {'username': r_username, "password": hashed_password, "backjoonId": r_baekjoonId}
    db.userInfo.insert_one(data)

    return jsonify({"result": 'success'})


# API #3: 스터디 메인 페이지
@app.route('/study/<int:study_number>', methods=['GET'])
def study_main(study_number):
    # 스터디 번호를 이용하여 스터디 정보를 렌더링
    return render_template('study_main.html', study_number=study_number)


# API #4: 스터디 추가
@app.route('/study/add', methods=['POST'])
@jwt_required()
def add_study():
    study_title = request.form['study_title']
    description = request.form['description']
    study_date = request.form['date']
    study_date = request.form['date']
    current_user = get_jwt_identity()
    user = db.userInfo.find_one({'username': current_user})
    backjoonid = user["backjoonId"]
    print(backjoonid)
    add_study_db(study_title, description, study_date, backjoonid)
    return jsonify({"result": 'success'})
    

# 언어에 따른 언어 ID 매핑
LANGUAGE_IDS = {
    'C++': 1001,
    'Java': 1002,
    'Python': 1003,
    'C': 1004,
    'Rust': 1005
}


# API #5: 스터디에 문제집 추가
@app.route('/workbook/add/<int:study_number>', methods=['POST'])
@jwt_required()
def add_workbook(study_number):
    data = request.json
    workbook_number = data.get('workbook_number')
    language = data.get('language')
    username = collection.find_one({'study_number': study_number})['backjoonid']
    
    url = "https://www.acmicpc.net/workbook/view/" + workbook_number
    session_obj = requests.Session()
    response = session_obj.get(url, headers = {"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        return jsonify({"msg": "없는 문제입니다."}),400

    language_id = LANGUAGE_IDS.get(language)
    if language_id is None:
        return 'Invalid Language', 400
    
    # print("workbook_number:", workbook_number)
    # print("language:", language)
    add_workbook_db(username, study_number, workbook_number, language_id)
    return jsonify({"result": 'success'})


# API #6: 스터디 모음 페이지
@app.route("/study/main", methods=["GET"])
@jwt_required()
def read():
    current_user = get_jwt_identity()
    user = db.userInfo.find_one({'username': current_user})
    username = user["backjoonId"]
    print(username)

    data = list(collection.find({'backjoonid' : username}))
    return jsonify({'result': 'success', 'data': data})


# API #5: 스터디 삭제
# @app.route("/study/delete", methods=['POST'])
# def delete_study():
#     print(1)
#     study_number = request.form['study_number']
    
#     study = collection.find_one({'study_number': study_number})
#     if not study:
#         return jsonify({'result': 'failure', 'message': 'Study not found'}), 404
    
#     # DB에서 스터디 삭제
#     result = collection.delete_one({'study_number': study_number})

#     if result.deleted_count == 1:
#         return jsonify({'result': 'success'})
#     else:
#         return jsonify({'result': 'failure', 'message': 'Failed to delete study'})

# API #5: 스터디 삭제
@app.route("/study/delete", methods = ['POST'])
def delete_study():
    print(request.json)
    study_id = request.json.get('_id')
    print("Deleting study with ID:", study_id)
   
    # DB에서 스터디 삭제
    result = collection.delete_one({'_id': ObjectId(study_id)})

    if result.deleted_count == 1:
        return jsonify({'result': 'success'})
    else:
        return jsonify({'result': 'failure', 'message': 'Failed to delete study'})


# API #7: 문제집 모음 페이지
@app.route("/workbook/main/<int:study_number>", methods=["GET"])
def show_workbooks(study_number):
    try:
        # 특정 스터디의 정보를 데이터베이스에서 가져옴
        study = collection.find_one({'study_number': study_number})
        
        # 스터디 정보와 워크북 정보를 HTML 템플릿에 전달하여 렌더링
        if study:
            workbooks_data = study.get('workbooks', [])
            return render_template('study_main.html', 
                                   study_number=study_number, 
                                   study_title=study.get('study_title', ''), 
                                   description=study.get('description', ''),
                                   date=study.get('study_date', ''),
                                   workbooks_data=workbooks_data)
        else:
            return jsonify({'result': 'failure', 'message': 'Study not found'}), 404
    except Exception as e:
        return str(e), 500

# API #8: 워크북 삭제
@app.route('/workbook/delete/<int:study_number>', methods=['POST'])
def delete_workbook(study_number):
    workbook_id = request.json.get('workbook_id')
    if not workbook_id:
        return jsonify({'result': 'failure', 'message': 'No workbook_id provided'}), 400
    
    study = collection.find_one({'study_number': study_number})
    if not study:
        return jsonify({'result': 'failure', 'message': 'Study not found'}), 404
    
    # 워크북 찾기
    workbook_to_delete = None
    workbooks = study.get('workbooks', [])
    for workbook in workbooks:
        if workbook.get('workbook_id') == workbook_id:
            workbook_to_delete = workbook
            break
    
    # 워크북을 못찾으면 실패
    if not workbook_to_delete:
        return jsonify({'result': 'failure', 'message': 'Workbook not found'}), 404
    
    # 워크북 삭제
    new_workbooks = [wb for wb in workbooks if wb != workbook_to_delete]
    result = collection.update_one(
        {'study_number': study_number},
        {'$set': {'workbooks': new_workbooks}}
    )
    
    if result.modified_count == 1:
        return jsonify({'result': 'success'})
    else:
        return jsonify({'result': 'failure', 'message': 'Failed to delete workbook'})




# 토큰을 저장하기 위한 변수 초기화
jwt_blocklist = set()

# API #8: 로그아웃
@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    jwt_blocklist.add(jti)
    return jsonify({'message': 'Logged out successfully'}), 200


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)



    