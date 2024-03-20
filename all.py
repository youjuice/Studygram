from bson import ObjectId
from flask import Flask, render_template, request, jsonify,redirect
from flask_cors import CORS
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from flask.json.provider import JSONProvider
import json
import jwt
from pymongo import MongoClient
import bcrypt
import requests
from datetime import timedelta

app = Flask(__name__)
CORS(app)
client = MongoClient('localhost', 27017)
db = client.dbstudy 
app.config["JWT_SECRET_KEY"] = "super-secret"
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
jwt = JWTManager(app)

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


@app.route('/login')
def hello_world():
    return render_template('login.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route("/tt", methods=["GET"])
@jwt_required()
def tt():
    token = request.headers.get("Authorization") 
    return "Success"

    

# API #2: 로그인 기능 구현      
@app.route('/login', methods=['POST'])
def login():
    username = request.form['usernames']
    password = request.form['passwords']

    # 사용자 이름을 기반으로 사용자 정보를 데이터베이스에서 가져옵니다.
    user = db.userInfo.find_one({'username': username})
    print(user)
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        # 비밀번호가 일치하는 경우 JWT 생성 및 반환
        access_token = create_access_token(identity=username)
        return jsonify({"result": "success", "access_token": access_token}), 200

    else:
        # 비밀번호가 일치하지 않는 경우
        return jsonify({"msg": "비밀번호가 틀립니다"}), 418
    
# # API #2-2: JWT 인증을 요구하는 라우트 보호
# @app.route('/protected', methods=['GET'])
# @jwt_required()
# def protected():
#     current_user = get_jwt_identity()
#     return jsonify(logged_in_as=current_user), 200

# API #2-3 : register
@app.route('/register', methods=['POST'])
def register():
    r_username = request.form['give_username']
    r_password = request.form['give_password']
    r_baekjoonId = request.form['give_baekjoonId']
    url = "https://www.acmicpc.net/user/"+r_baekjoonId

    session_obj = requests.Session()
    response = session_obj.get(url, headers = {"User-Agent": "Mozilla/5.0"})
    
    if response.status_code != 200:
        return jsonify({"error": "백준에 없는 사용자입니다."}), 408
    existing_user = db.userInfo.find_one({'username': r_username})
    if existing_user:
        return jsonify({"error": "이미 존재하는 사용자입니다"}), 405

    existing_baekjoonId = db.userInfo.find_one({'backjoonId': r_baekjoonId})
    if existing_baekjoonId:
        return jsonify({"error": "이미 존재하는 사용자입니다"}), 407    
    

    hashed_password = bcrypt.hashpw(r_password.encode('utf-8'), bcrypt.gensalt())
    data = {'username': r_username, "password": hashed_password, "backjoonId": r_baekjoonId}

    db.userInfo.insert_one(data)
    return jsonify({"result": 'success'})


if __name__ == '__main__':
    app.run(debug=True)