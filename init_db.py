import random
import requests
import threading
import time

from flask import Flask
app = Flask(__name__)

from bs4 import BeautifulSoup
from pymongo import MongoClient  

client = MongoClient('localhost', 27017)
db = client.studygram
collection = db['study']

global username
username = None

# 1. 데이터베이스에 스터디북 추가
def add_study_db(title, description, study_date, backjoonid):
    try:
        study_count = collection.count_documents({})
        study_number = study_count + 1
        
        study = {
            'study_number': study_number,
            'study_title': title,
            'study_date': study_date,
            'description': description,
            'backjoonid': backjoonid
        }
        
        result = collection.insert_one(study)
        study_id = result.inserted_id
        
        print("Study data updated and saved to MongoDB")
        print("New study ID: ", study_id)
        
    except Exception as e:
        print("Error:", e)

# 2. 스터디 북에 문제집 추가
def add_workbook_db(username, study_number, workbook_number, language_id):
    try:
        # 백준 문제집 정보 크롤링 (제목, 문제 수)
        headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
        url = f"https://www.acmicpc.net/workbook/view/{workbook_number}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(username)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_element = soup.select_one('body > div.wrapper > div.container.content > div.row > div:nth-child(2) > div > h1 > span:nth-child(1)')
        if title_element:
            problem_title = title_element.text.strip()
            # print(problem_title)
        else:
            problem_title = None
        
        problem_list = soup.select('body > div.wrapper > div.container.content > div.row > div:nth-child(3) > div > table > tbody > tr')
        problem_numbers = []
        
        for tr in problem_list:
            td = tr.find('td')
            problem_number = td.text.strip()
            problem_numbers.append(problem_number)
            
        total_problems = len(problem_numbers)
        
        # 해당 문제집의 진행률 크롤링 (언어별 & 사용자별)
        url = f'https://www.acmicpc.net/status?problem_id=&user_id={username}&language_id={language_id}'
        total_success_count = 0
        
        # 모든 페이지 크롤링
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            submission_rows = soup.select('tr[id^="solution"]')
            if not submission_rows:
                break  # 페이지가 존재하지 않으면 중단
            
            for row in submission_rows:
                success_count = 0
                for problem_number in problem_numbers:
                    problem_element = soup.select_one(f'a[href="/problem/{problem_number}"]')
                    
                    if problem_element:
                        result_element = problem_element.find_next('span', class_='result-text')
                        
                        if result_element and 'result-ac' in result_element.get('class', []):
                            success_count += 1
                            
            total_success_count += success_count
            url = get_next_page_url(response)   # 다음 페이지 크롤링
        
        success_ratio = 100 * (total_success_count / total_problems) if total_problems > 0 else 0
        # print(f'{total_success_count}/{total_problems}')
        # print(f'{success_ratio}%')

        # MongoDB에 데이터 저장
        workbook = {
            'workbook_number': workbook_number,
            'workbook_title': problem_title,
            'success_ratio': success_ratio,
            'language': language_id
        }
        
        collection.update_one(
            {'study_number': study_number},
            {'$push': {'workbooks': workbook}}
        )
        # print("Workbook data saved to Study number: ", study_number)
    
    except Exception as e:
        print("Error:", e)

# 모든 페이지의 데이터를 크롤링하기 (다음 페이지로 이동하는 함수)
def get_next_page_url(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    next_page_link = soup.select_one('a#next_page')
    if next_page_link:
        return 'https://www.acmicpc.net' + next_page_link['href']
    return None

# 함수 호출 예시
# add_study_db('기초 스터디', '초보 탈출 기원', '2024.08.19 - 2024.09.19') 
# add_workbook_db('yooju00', 3, 9528, 1003)
