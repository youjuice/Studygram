from flask import Flask, render_template, jsonify, request, session
from flask.json.provider import JSONProvider
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

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

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
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


# API #3: 스터디 메인 페이지
@app.route('/study/<int:study_number>', methods=['GET'])
def study_main(study_number):
    # 스터디 번호를 이용하여 스터디 정보를 렌더링
    return render_template('study_main.html', study_number=study_number)

# API #4: 스터디 추가
@app.route('/study/add', methods=['POST'])
def add_study():
    study_title = request.form['study_title']
    description = request.form['description']
    date = request.form['date']
    
    add_study_db(study_title, description, date)
    return 'Study added successfully! Study ID: {study_id}'

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
def add_workbook(study_number):
    workbook_number = request.form['workbook_number']
    language = request.form['language']
    username = session.get['username']
    
    language_id = LANGUAGE_IDS.get(language)
    if language_id is None:
        return 'Invalid Language', 400
    
    add_workbook_db(username, study_number, workbook_number, language_id)
    return 'Workbook added successfully!'

if __name__ == '__main__':
    app.run(debug=True)
