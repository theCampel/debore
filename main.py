from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import sys
import re
import requests
import os
import json
from urllib.parse import urljoin
from datetime import datetime

from config import INSTITUTION_URL, DOWNLOAD_DIR

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
    sleep_interval = 5
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

def get_available_courses(driver):
    """Get all available courses and their links from the courses page."""
    print("Fetching available courses...")
    
    # Wait for the grid to load
    wait = WebDriverWait(driver, 20)
    try:
        # Wait for grid courses to load
        grid = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="grid"]')))
        
        # helps reliability
        time.sleep(1)
        
        # Find all spans containing course links
        course_spans = grid.find_elements(By.CSS_SELECTOR, 'div[role="row"] span a[href*="/section/"]')
        
        if not course_spans:
            print("No course elements found. DOM structure:")
            print(grid.get_attribute('outerHTML'))
            return []
            
        courses = {}
        for span in course_spans:
            try:
                course_name = span.get_attribute('aria-label')
                course_url = span.get_attribute('href')
                
                if course_name and course_url:
                    courses[course_name] = course_url
                    
            except Exception as e:
                print(f"Error processing course element: {str(e)}")
                continue
        
        print(f"Successfully found {len(courses)} courses")
        return courses
        
    except Exception as e:
        print(f"Failed to find courses page: {str(e)}")
        # Print the current URL to help with debugging
        print(f"Current URL: {driver.current_url}")
        return []

def display_and_choose_course(courses):
    """Display all available courses with numbers and let user choose one."""
    if not courses:
        print("No courses available.")
        return None
    
    # Print all courses with numbers
    for i, course_name in enumerate(courses.keys(), 1):
        print(f"{i}. {course_name}")
    
    # Get user input
    choice = input("Enter the number of the course you want to download: ")


    # Return the selected course U
    return courses[list(courses.keys())[int(choice) - 1]]

def get_course_lectures_data(session, course_url):
    """Get all lecture data for a given course URL"""
    syllabus_url = course_url[:-5] + '/syllabus'
    print(syllabus_url)

    response = session.get(syllabus_url)
    
    if not response.ok:
        print(f"Failed to get syllabus: {response.status_code}")
        return []
    
    try:
        data = response.json()
    except Exception as e:
        print(f"Failed to parse syllabus as JSON: {str(e)}")
        return []
    
    lectures = data.get('data', [])  # Changed default to empty list
    lecture_data = []
    
    for lecture in lectures:
        try:
            lesson = lecture.get('lesson', {})
            lesson_info = lesson.get('lesson', {})
            
            # Extract relevant information
            lecture_info = {
                'name': lesson_info.get('displayName', ''),
                'id': lesson_info.get('id', ''),
                'start_time': lesson_info.get('timing', {}).get('start', ''),
                'end_time': lesson_info.get('timing', {}).get('end', ''),
                'timezone': lesson_info.get('timeZone', {}).get('name', '')
            }
            
            # Get media information if available
            medias = lesson.get('medias', [])
            for media in medias:
                if media.get('mediaType') == 'Video' and media.get('isAvailable'):
                    lecture_info['video_id'] = media.get('id', '')
                    lecture_info['video_title'] = media.get('title', '')
                    lecture_info['thumbnail'] = media.get('thumbnailUri', '')
                    break  # Only get the first available video
            
            if lecture_info.get('video_id'):  # Only add lectures with available videos
                lecture_data.append(lecture_info)
                
        except Exception as e:
            print(f"Error processing lecture: {str(e)}")
            continue
    
    print(lecture_data)
    return lecture_data

def download_lecture(session, lecture_url, output_dir):
    """Download a lecture, given a lecture URL"""
    response = session.get(lecture_url)

    if not response.ok:
        print(f"Failed to download lecture: {response.status_code}")
        return False
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    wrote = 0
    with open(output_dir, 'wb') as f:
        for data in response.iter_content(block_size):
            wrote += len(data)
            f.write(data)

            # Print progress
            if total_size:
                progress = (wrote / total_size) * 100
                sys.stdout.write(f"\rDownload Progress: {progress:.1f}%")
                sys.stdout.flush()

    print("\nDownload complete!")
    return True


def main():
    driver = setup_driver()
    success, session = login_echo360_sso(driver, INSTITUTION_URL)
    
    if not success:
        print("Failed to log in")
        driver.quit()
        sys.exit(1)
    
    courses = get_available_courses(driver)
    
    selected_course_url = display_and_choose_course(courses)

    lecture_data = get_course_lectures_data(session, selected_course_url)
    print(lecture_data)

    # if selected_course_url:
    #     video_url = INSTITUTION_URL + selected_course_url
    #     download_lecture(session, video_url, DOWNLOAD_DIR)

    # Clean up
    driver.quit()

if __name__ == '__main__':
    main()
