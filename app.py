from flask import Flask, render_template, jsonify, request, session, make_response
from flask.json.provider import JSONProvider
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from bson import ObjectId, json_util
from pymongo import MongoClient
from bs4 import BeautifulSoup
from init_db import add_workbook_db, add_study_db

import requests
import json
import sys

app = Flask(__name__)
jwt = JWTManager(app)

client = MongoClient('localhost', 27017)
db = client.studygram
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

# API #1: 메인 페이지
@app.route('/')
def home():
    return render_template('index.html')

# API #2: 로그인 기능 구현


# API #3: 스터디 추가
@app.route('/study/add', methods=['POST'])
def add_study():
    study_title = request.form['study_title']
    description = request.form['description']
    study_date = request.form['date']
    
    add_study_db(study_title, description, study_date)
    return jsonify({"result": 'success'})


# API #4: 스터디 모음 페이지
@app.route("/study/main", methods = ["GET"])
def read():
    data = list(collection.find({}))
    return jsonify({'result': 'success', 'data': data})


# API #5: 스터디 삭제
@app.route("/study/delete", methods = ['POST'])
def delete_study():
    study_id = request.json.get('_id')
    print("Deleting study with ID:", study_id)
   
    # DB에서 스터디 삭제
    result = collection.delete_one({'_id': ObjectId(study_id)})

    if result.deleted_count == 1:
        return jsonify({'result': 'success'})
    else:
        return jsonify({'result': 'failure', 'message': 'Failed to delete study'})


# 언어에 따른 언어 ID 매핑
LANGUAGE_IDS = {
    'C++': 1001,
    'Java': 1002,
    'Python': 1003,
    'C': 1004,
    'Rust': 1005
}

# API #6: 스터디에 문제집 추가
@app.route('/workbook/add/<int:study_number>', methods=['POST'])
def add_workbook(study_number):
    data = request.json
    workbook_number = data.get('workbook_number')
    language = data.get('language')
    username = "yooju00"
    
    language_id = LANGUAGE_IDS.get(language)
    if language_id is None:
        return 'Invalid Language', 400
    
    # print("workbook_number:", workbook_number)
    # print("language:", language)
    add_workbook_db(username, study_number, workbook_number, language_id)
    return jsonify({"result": 'success'})


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

    
if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)
    