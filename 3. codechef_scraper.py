from typing import Dict, List, Union
import logging
import json
import time
import requests
import boto3
from playwright.sync_api import sync_playwright

# Global variables initialization
def global_vars() -> None:
    """Initialize global variables."""
    # Credentials
    global CODECHEF_MAIL_OR_USERNAME, CODECHEF_PASSWORD
    CODECHEF_MAIL_OR_USERNAME = 'your_codechef_username'
    CODECHEF_PASSWORD = 'your_codechef_password'

    # Page offsets
    global START_PAGE, END_PAGE
    START_PAGE = 44
    END_PAGE = 150
    
    # Browser configuration
    global HEADLESS_OPTION
    HEADLESS_OPTION = True

    # AWS configuration
    global S3, S3_FOLDER_PATH, BUCKET
    AWS_ACCESS_KEY = "your_aws_access_key"
    AWS_SECRET_KEY = "your_aws_secret_key"
    AWS_REGION = "your_aws_region"
    BUCKET = "your_s3_bucket_name"
    S3 = boto3.client(
        's3', 
        aws_access_key_id=AWS_ACCESS_KEY, 
        aws_secret_access_key=AWS_SECRET_KEY, 
        region_name=AWS_REGION
        )
    S3_FOLDER_PATH = "your_s3_folder_path"
    
    # Logging
    global LOG_FILE_DIR
    LOG_FILE_DIR = "path_to_log_file.log"
    
    # Request headers
    global HEADERS
    HEADERS = {
        'cookie' : None,
        'x-csrf-token' : None
        }

# Initialize logging
def initialize_logging(log_file_dir: str) -> None:
    """Initialize logging configuration."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s -- %(message)s', '%Y-%m-%d %H:%M:%S')
    
    file_handler = logging.FileHandler(log_file_dir)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    logging.info('Initializing logging file')
    logging.info('------------------------------------NEW LOG----------------------------------\n\n')

# Request handler for playwright
def playwright_request_handler(request) -> None:
    """Handle requests from playwright."""
    try:
        global HEADERS
        cookie = request.header_value("cookie")
        csrf_token = request.header_value("x-csrf-token")
        if cookie and csrf_token:
            HEADERS['cookie'] = cookie
            HEADERS['x-csrf-token'] = csrf_token
    except:
        pass

# Fetch headers using playwright
def fetch_headers() -> None:
    """Fetch headers using playwright."""
    logging.info('Fetching headers')
    with sync_playwright() as playwright:
        logging.info('Launching browser')
        browser = playwright.chromium.launch(headless=HEADLESS_OPTION)
        context = browser.new_context()
        page = context.new_page()
        sample_problem_url = "https://www.codechef.com/problems/FOODCOST"
        logging.info('Redirecting to sample problem URL')
        page.goto(sample_problem_url)
        logging.info('Moving to submissions tab')
        page.get_by_role("tab", name="Submissions").click()
        page.get_by_role("button", name="Log In").click()
        logging.info('Entering credentials')
        page.locator("input[type=\"text\"]").fill(CODECHEF_MAIL_OR_USERNAME)
        page.locator("input[type=\"password\"]").fill(CODECHEF_PASSWORD)
        page.get_by_role("button", name="LOGIN").click()
        logging.info('Waiting to fetch cookie and CSRF-token (10 seconds)')
        try: page.on("request", playwright_request_handler)
        except: pass
        time.sleep(10)
        logging.info('Closing browser')
        context.close()
        browser.close()

# Fetch problem list
def get_problem_list(page_number: int) -> List[Dict[str, Union[str, int]]]:
    """Get the list of problems from a specific page."""
    logging.info(f'Getting problem list (Page {page_number})')
    url = "https://www.codechef.com/api/list/problems"
    params = {
        'limit' : 50,
        'page' : page_number
    }
    problem_list = requests.request(
        "GET", 
        url, 
        params=params
        ).json()
    return problem_list.get('data')

# Fetch problem details
def get_problem(slug: str) -> Dict[str, Union[str, Dict[str, str]]]:
    """Get details of a specific problem."""
    logging.info(f'Getting problem details (Problem slug: {slug})')
    problem = requests.request(
        'GET',
        f'https://www.codechef.com/api/contests/PRACTICE/problems/{slug}'
        ).json()
    return problem

# Fetch submission list
def get_submission_list(slug: str) -> List[Dict[str, str]]:
    """Get a list of submissions for a specific problem."""
    count = 0
    page = 1
    submissions = []
    previous_submission = None
    while count <= 5:
        if page > 25:
            break
        logging.info(f'Getting submissions list (Problem slug: {slug}, Page: {page})')
        submission_list = requests.request(
            'GET',
            f'https://www.codechef.com/api/submissions/PRACTICE/{slug}?limit=10&page={page}',
            headers = HEADERS
            ).json()
        if submission_list.get('status') == 'apierror':
            fetch_headers()
            get_submission_list(slug)
        submission_list = submission_list.get('data')
        if previous_submission == submission_list:
            break
        previous_submission = submission_list
        if not submission_list:
            break
        for submission in submission_list:
            if submission.get('tooltip') == 'accepted':
                submissions.append(submission)
                count += 1
                if count >= 5:
                    break
        page += 1
    return submissions

# Fetch submission details
def get_submission(submission_code: str, index: int) -> Dict[str, str]:
    """Get details of a specific submission."""
    logging.info(f'Getting submission details [{index}] (Submission code: {submission_code})')
    submission = requests.request(
        'GET',
        f'https://www.codechef.com/api/submission-code/{submission_code}'
        ).json().get('data')
    return submission

# List objects in S3 bucket
def get_objects_list(s3_key: str) -> List[str]:
    """List objects in a specific S3 bucket path."""
    logging.info(f"Getting objects in path (S3 path: {s3_key})")
    object_list = []
    continuation_token = None

    while True:
        if continuation_token:
            response = S3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=s3_key,
                ContinuationToken=continuation_token
            )
        else:
            response = S3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=s3_key
            )
        if 'Contents' in response:
            for obj in response['Contents']:
                object_list.append(obj['Key'])
        if not response.get('IsTruncated'):
            break
        continuation_token = response['NextContinuationToken']

    return object_list[1:]

# Upload JSON data to S3 bucket
def upload_json_to_s3(s3_key: str, data: Dict) -> None:
    """Upload JSON data to a specific S3 bucket path."""
    S3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, indent=4),
        ContentType='application/json'
    )
    logging.info(f"Uploaded file (S3 key: {s3_key})")

if __name__ == '__main__':
    
    global_vars()
    initialize_logging(LOG_FILE_DIR)
    fetch_headers()
        
    while START_PAGE <= END_PAGE:
        
        problem_list = get_problem_list(START_PAGE)
        
        for problem in problem_list:
            
            start_time = time.time()
            
            problem_data = dict()
            
            problem_data['title'] = problem.get('name')
            problem_data['title_slug'] = problem.get('code')
            
            uploaded_list = get_objects_list(S3_FOLDER_PATH)
            s3_key = S3_FOLDER_PATH + '/' + problem_data.get("title_slug") + '.json'
            if s3_key in uploaded_list:
                logging.info(f'File already present (File: {s3_key})')
                continue
            
            problem_info = get_problem(problem_data.get('title_slug'))
            
            problem_data['difficulty_rating'] = problem.get('difficulty_rating')
            problem_data['difficulty_threshold'] = problem_info.get('difficultyThreshold')
            
            source = dict()
            source['total_submissions'] = problem.get('total_submissions')
            source['successful_submissions'] = problem.get('successful_submissions')
            source['distinct_successful_submissions'] = problem.get('distinct_successful_submissions')
            source['partially_successful_submissions'] = problem.get('partially_successful_submissions')
            source['max_timelimit'] = problem_info.get('max_timelimit')
            source['source_sizelimit'] = problem_info.get('source_sizelimit')
            source['problem_author'] = problem_info.get('problem_author')
            source['date_added'] = problem_info.get('date_added') 
            source['intended_contest_id'] = problem.get('intended_contest_id')
            source['actual_intended_contests'] = problem.get('actual_intended_contests')
            source['contest_code'] = problem.get('contest_code')
            source['category_name'] = problem_info.get('category_name')
            source['contest_category'] = problem_info.get('contest_category')
            source['votes_data'] = problem_info.get('votes_data')
            source['visited_contests'] = problem_info.get('visitedContests')
            source['is_supported_by_judge'] = problem_info.get('isSupportedByJudge')
            problem_data['source'] = source
            
            problem_data['constraints'] = problem_info.get('problemComponents').get('constraints')
            problem_data['problem_description'] = problem_info.get('problemComponents').get('statement')
            problem_data['input_format'] = problem_info.get('problemComponents').get('inputFormat')
            problem_data['output_format'] = problem_info.get('problemComponents').get('outputFormat')
            problem_data['testcases'] = problem_info.get('problemComponents').get('sampleTestCases')
            problem_data['special_testcases'] = problem_info.get('specialTestCases')
            problem_data['hints'] = problem_info.get('hints')
            problem_data['cheat_codes'] = problem_info.get('cheatCodes')
            try:
                problem_data['available_languages'] = problem_info.get('languages_supported').split(', ')
            except:
                problem_data['available_languages'] = problem_info.get('languages_supported')

            submissions_list = get_submission_list(problem_data.get('title_slug'))
            user_solutions = dict()
            index = 1
            for submission in submissions_list:
                submission = get_submission(submission.get('id'), index)
                index += 1
                try:
                    language = submission.get('language').get('full_name')
                    if language not in user_solutions:
                        user_solutions[language] = []
                    code = submission.get('code')
                    if code not in user_solutions.get(language):
                        user_solutions[language].append(submission.get('code'))
                except:
                    print(json.dumps(submission, indent=4))
            problem_data['user_solutions'] = user_solutions
            
            upload_json_to_s3(s3_key, problem_data)
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            
            logging.info(f"Completed {problem_data.get('title_slug')} in {minutes} mins {seconds} secs")
            
        START_PAGE += 1