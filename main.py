from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import time
import sys
import re
import requests
import os
import pickle
import json

def setup_driver():
    options = Options()
    # Uncomment the next line to run Firefox in headless mode
    # options.headless = True
    driver = webdriver.Firefox(options=options)
    return driver


def login_echo360_sso(driver, institution_url):
    driver.get(institution_url)
    
    print("Please log in using your institution's SSO in the browser window that opened.")
    print("The script will automatically proceed once you have logged in.")

    max_wait_time = 300
    wait_time = 0
    sleep_interval = 2

    while wait_time < max_wait_time:
        cookies = driver.get_cookies()
        if any(cookie['name']=='ECHO_JWT' for cookie in cookies):
            print("Login successful - Browser authenticated")
            session = requests.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            return True, session
        
        wait_time += sleep_interval
        time.sleep(sleep_interval)

    print("Login failed / timed out")
    return False, None

def get_lectures(session, section_url):
    # Extract hostname and section UUID from the section URL
    match = re.match(r'(https://[^/]+)/section/([^/]+)/', section_url)
    if not match:
        print("Invalid section URL")
        return

    hostname = match.group(1)
    section_uuid = match.group(2)

    syllabus_url = f"{hostname}/section/{section_uuid}/syllabus"


    
    # Make a GET request to the syllabus URL
    response = session.get(syllabus_url)
    
    if not response.ok:
        print("Failed to get syllabus data")
        print("Response status code:", response.status_code)
        return

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        print("Failed to parse syllabus data as JSON.")
        print("Response status code:", response.status_code)
        print("Response headers:", response.headers)
        print("Response text:", response.text)  # Print first 500 chars
        return

    # Now parse the data to extract lecture information
    lectures = data.get('data', [])

    if not lectures:
        print("No lectures found.")
        return

    print("Lectures:")
    for lecture in lectures:
        # Each lecture is a dictionary with various keys
        # Extract relevant information
        try:
            lesson = lecture.get('lesson', {})
            lesson_info = lesson.get('lesson', {})
            display_name = lesson_info.get('displayName', 'No Title')
            start_time = lesson_info.get('startTimeUTC', 'No Date')
            duration = lesson_info.get('duration', 'No Duration')
            print(f"Title: {display_name}")
            print(f"Start Time: {start_time}")
            print(f"Duration: {duration} seconds")
            print("-" * 40)
        except KeyError as e:
            print(f"Key error: {e}")
            pass

def main():
    institution_url = 'https://echo360.org.uk/'
    section_url = 'https://echo360.org.uk/section/3cb6a06d-bd07-4fca-a744-b6712432bf9a/home'

    driver = setup_driver()
    success, session = login_echo360_sso(driver, institution_url)
    if not success:
        print("Failed to log in")
        driver.quit()
        sys.exit()

    get_lectures(session, section_url)

    # Clean up
    driver.quit()

if __name__ == '__main__':
    main()
