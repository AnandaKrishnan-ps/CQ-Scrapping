from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
import time
import json
import logging
import boto3
import os
import sys
from playwright.sync_api import BrowserContext, Page, Browser
from typing import Dict, List, Tuple, Union

def global_vars() -> None:
    """
    This function initializes the global variables used throughout the code.

    Returns:
        None
    """
    # GFG -- CREDENTIALS
    global GFG_MAIL_OR_USERNAME, GFG_PASSWORD
    GFG_MAIL_OR_USERNAME = 'your_geeksforgeeks_email@example.com'
    GFG_PASSWORD = 'your_geeksforgeeks_password'

    # OFFSETS
    global START_PAGE, END_PAGE
    START_PAGE = 33
    END_PAGE = 50

    # BROWSER
    global HEADLESS_OPTION
    HEADLESS_OPTION = True

    # AWS
    global BUCKET
    AWS_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY"
    AWS_SECRET_KEY = "YOUR_AWS_SECRET_KEY"
    AWS_REGION = "YOUR_AWS_REGION"
    BUCKET = "your_s3_bucket_name"

    # AWS
    global S3, S3_FOLDER_PATH, BUCKET
    AWS_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY"
    AWS_SECRET_KEY = "YOUR_AWS_SECRET_KEY"
    AWS_REGION = "YOUR_AWS_REGION"
    BUCKET = "your_s3_bucket_name"
    S3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )
    S3_FOLDER_PATH = "your s3 folder path to store"

    # LOGGING
    global LOG_FILE_DIR
    LOG_FILE_DIR = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.path.basename(os.path.abspath(__file__)).replace('.py', '.log')
    )

    # COOKIES
    global PROBLEM_COOKY_NEEDED, SUBMISSION_COOKY_NEEDED
    PROBLEM_COOKY_NEEDED = {
        "_gcl_au",
        "gfg_nluid",
        "_cc_id",
        "default_lang",
        "gfg_theme",
        "g_state",
        "_fbp",
        "_tgpc",
        "gfg_ugen",
        "gfg_utype",
        "gfg_ugy",
        "gfg_uspl_1",
        "gfg_uspl_2",
        "gfg_uspl_3",
        "FCNEC",
        "__gads",
        "__gpi",
        "__eoi",
        "_gcl_aw",
        "_gac_UA-71763465-1",
        "gfg_id5_identity",
        "_ga_6K5G5NTXFT",
        "_ga_DWCCJLKX3X",
        "http_referrer",
        "_clck",
        "_gid",
        "authtoken",
        "_ga",
        "_tguatd",
        "_tgaid",
        "_tgidts",
        "_tglksd",
        "_uetsid",
        "_uetvid",
        "_gat_gtag_UA_71763465_1",
        "_clsk",
        "_tgsid",
        "gfguserName",
        "_ga_SZ454CLTZM",
        "_ga_EPYP889PQW"
    }
    SUBMISSION_COOKY_NEEDED = {
        "gfg_nluid",
        "_fbp",
        "_gcl_au",
        "_gid",
        "_tgpc",
        "gfg_id5_identity",
        "gfg_ugy",
        "_gcl_aw",
        "_gac_UA-71763465-1",
        "__gads",
        "__gpi",
        "__eoi",
        "_clck",
        "gfgpromoparams",
        "_tglksd",
        "g_state",
        "_ga_6K5G5NTXFT",
        "_ga_DWCCJLKX3X",
        "authtoken",
        "gfguserName",
        "http_referrer",
        "gfg_theme",
        "_ga_EPYP889PQW",
        "_ga",
        "_uetsid",
        "_uetvid",
        "_ga_SZ454CLTZM",
        "_clsk"
    }

def initialize_logging(log_file_dir: str) -> None:
    """
    This function initializes the logging system.

    Args:
        log_file_dir (str): The directory path where the log file will be stored.

    Returns:
        None
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s -- %(message)s', '%Y-%m-%d %H:%M:%S')

    file_handler = logging.FileHandler(log_file_dir)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logging.info('LOCAL --> INITIALIZING LOGGING FILE')
    logging.info('------------------------------------NEW LOG----------------------------------\n\n')
# Open browser using Playwright
def open_browser(headless_option: bool) -> Tuple[Page, BrowserContext, Browser]:
    """
    This function launches a new browser instance using Playwright and creates a new page and context.

    Args:
        headless_option (bool): A boolean value indicating whether to launch the browser in headless mode or not.

    Returns:
        Tuple[Page, Context, Browser]: A tuple containing the new page, context, and browser instance.
    """
    logging.info(f'BROWSER --> LAUNCHING')
    browser = p.chromium.launch(headless=headless_option)
    logging.info(f'BROWSER --> CREATING A NEW PAGE & CONTEXT')
    context = browser.new_context()
    page = context.new_page()
    return page, context, browser
# Login to GeeksforGeeks
def login_to_gfg(page: Page, email: str, password: str) -> None:
    """
    This function logs into the GeeksforGeeks website using the given email and password.

    Args:
        page (Page): The Playwright page object.
        email (str): The GeeksforGeeks email address.
        password (str): The GeeksforGeeks password.

    Returns:
        None
    """
    gfg_auth_url = "https://auth.geeksforgeeks.org/?to=https://www.geeksforgeeks.org/"
    logging.info("BROWSER --> GOING TO AUTHENTICATION PAGE")
    page.goto(gfg_auth_url, wait_until="domcontentloaded")
    logging.info("BROWSER --> ENTERING CREDENTIALS")
    page.get_by_placeholder("Username or email").fill(email)
    page.get_by_role("textbox", name="Password").fill(password)
    logging.info("BROWSER --> SIGNING IN")
    page.get_by_role("button", name="Sign In").click()    

def get_problem_list(page_number: int) -> Dict:
    """
    This function makes a GET request to the GeeksforGeeks API to retrieve a list of problems.

    Args:
        page_number (int): The page number of the problem list to retrieve.

    Returns:
        dict: A dictionary containing the problem data.
    """
    logging.info(f'API --> GETTING PROBLEM PAGE --{page_number}')
    url = 'https://practiceapi.geeksforgeeks.org/api/vr/problems/'
    params = {
        'pageMode': 'explore',
        'page': str(page_number),
    }
    headers = {
        'origin': 'https://www.geeksforgeeks.org'
    }
    response = requests.get(url, params=params, headers=headers).json()
    return response.get('results')    

def get_cookies(context: BrowserContext, cooky: str) -> Dict[str, str]:
    """Get cookies from the browser context.

    Args:
        context (BrowserContext): The browser context from which to get the cookies.
        cooky (str): The type of cookies to retrieve, either 'problem' or 'submission'.

    Returns:
        Dict[str, str]: A dictionary containing the cookies, where the key is the cookie name and the value is the cookie value.
    """
    global PROBLEM_COOKY_NEEDED, SUBMISSION_COOKY_NEEDED
    if cooky == 'problem':
        cookies_needed = PROBLEM_COOKY_NEEDED
    elif cooky == 'submission':
        cookies_needed = SUBMISSION_COOKY_NEEDED
    cookies = {
        cooky.get('name'): cooky.get('value')
        for cooky in context.cookies()
        if cooky.get('name') in cookies_needed
    }
    return cookies    
# Open all API gateways for problem submissions
def open_all_api_gateways(page: Page, submission_time: str, status: str) -> None:
    """Opens all API gateways for problem submissions.

    Args:
        page (Page): The Playwright page object.
        submission_time (str): The submission time of the submission to open the API gateways for.
        status (str): The status of the submission to open the API gateways for.
    """
    page.get_by_text("Submissions", exact=True).click()
    page.get_by_text("All Submissions").click()
    page.get_by_role("row", name=f"{submission_time} {status}").locator("a").nth(1).click()
    page.get_by_role("button", name="OK", exact=True).click()
    
# Get problem HTML content
def get_problem_html(problem_url: str) -> str:
    """
    This function retrieves the HTML content of a GeeksforGeeks problem page.

    Args:
        problem_url (str): The URL of the GeeksforGeeks problem page.

    Returns:
        str: The HTML content of the problem page.
    """
    html = requests.request("GET", problem_url).text
    soup = BeautifulSoup(html, 'html.parser')
    script_element = soup.find('script', id='__NEXT_DATA__')
    json_content = json.loads(script_element.string)
    prob_html = json_content.get('props').get('pageProps').get('initialState').get('problemData').get('allData').get('probData').get('problem_question')
    return prob_html
    
# Get problem data including submissions
def get_problem_data(problem_url: str, slug: str, context: BrowserContext, page: Page) -> Tuple[Dict, Dict]:
    """
    This function retrieves the metadata and submission data of a GeeksforGeeks problem.

    Args:
        problem_url (str): The URL of the GeeksforGeeks problem page.
        slug (str): The unique slug of the problem.
        context (BrowserContext): The Playwright browser context.
        page (Page): The Playwright page object.

    Returns:
        Tuple[Dict, Dict]: A tuple containing the problem metadata and submission data. The metadata is stored in a dictionary, and the submission data is stored in a dictionary, where the key is the language and the value is a list of submission codes.
    """
    logging.info(f'BROWSER --> GOING TO THE PROBLEM URL {problem_url}')
    page.goto(problem_url, wait_until="domcontentloaded")  # Open the problem page in the browser
    logging.info('BROWSER --> WAITING FOR COOKIE GENERATION (20 SECONDS)')
    time.sleep(20)  # Wait for 20 seconds to allow for cookie generation
    problem_meta = requests.request(
        'GET',  # Make a GET request
        url=f"https://practiceapi.geeksforgeeks.org/api/latest/problems/{slug}/metainfo/",  # to the GFG API endpoint
        cookies=get_cookies(context, 'submission')  # with the submission cookies
    ).json().get('results')  # Parse the JSON response

    problem_id = problem_meta.get('id')  # Get the problem ID
    submissions_100 = dict()  # Initialize an empty dictionary to store the submission data
    count = 0  # Initialize a counter to track the number of submissions retrieved
    params = {}  # Initialize an empty dictionary to store the query parameters
    submissions = True  # Initialize a boolean variable to track whether there are more submissions to retrieve
    cookies = get_cookies(context, 'submission')  # Get the submission cookies
    submissions = requests.request(
        'GET',  # Make a GET request
        url=f"https://practiceapi.geeksforgeeks.org/api/latest/problems/{problem_id}/submissions/",  # to the GFG API endpoint
        cookies=cookies,  # with the submission cookies
        params=params  # with the query parameters
    ).json().get('message').get('submissions').get('Items')  # Parse the JSON response

    first_sub_time = submissions[0].get('subtime')  # Get the first submission time
    first_status = submissions[0].get('exec_status_text')  # Get the first submission status
    open_all_api_gateways(page, first_sub_time, first_status)  # Open all API gateways for the first submission

    while count <= 5:  # Loop through up to 5 submissions
        submissions = requests.request(
            'GET',  # Make a GET request
            url=f"https://practiceapi.geeksforgeeks.org/api/latest/problems/{problem_id}/submissions/",  # to the GFG API endpoint
            cookies=cookies,  # with the submission cookies
            params=params  # with the query parameters
        ).json().get('message').get('submissions')  # Parse the JSON response
        last_keys = submissions.get('LastEvaluatedKey')  # Get the last evaluated key
        submissions = submissions.get('Items')  # Get the submissions
        if not submissions:  # Check if there are any more submissions
            break
        for submission in submissions:  # Loop through the submissions
            language = submission.get('lang')  # Get the language of the submission
            submission_id = submission.get('submission_id')  # Get the submission ID
            logging.info(f'API --> GOING THROUGH SUBMISSION ID : {submission_id}')
            status = submission.get('exec_status_text')  # Get the execution status of the submission
            if status == 'Correct':  # Check if the submission is correct
                submission_data = requests.request(
                    'GET',  # Make a GET request
                    url=f"https://practiceapi.geeksforgeeks.org/api/latest/problems/submissions/{submission_id}/",  # to the GFG API endpoint
                    cookies=cookies  # with the submission cookies
                ).json()  # Parse the JSON response
                submission_codes = {
                    'gfg_code': submission_data.get('code'),  # Get the GFG code
                    'user_code': submission_data.get('user_code')  # Get the user code
                }
                if language not in submissions_100:  # Check if the language is already in the dictionary
                    submissions_100[language] = list()  # Add the language to the dictionary if it is not already present
                submissions_100[language].append(submission_codes)  # Add the submission codes to the dictionary
                count += 1  # Increment the counter
                if count > 5:  # Check if the counter is greater than 5
                    break
        params = {
            'last_submission_key': last_keys.get('submission_id'),  # Set the last submission key parameter
            'last_submission_key_time': last_keys.get('subtime').replace(' ', '%')  # Set the last submission key time parameter
        }
    return problem_meta, submissions_100  # Return the problem metadata and submission data

def get_data_from_html(html: str) -> Tuple[str, List[str], Dict[str, str]]:
    """
    This function extracts the problem description, constraints, and example code from the given HTML content.

    Args:
        html (str): The HTML content of the GeeksforGeeks problem page.

    Returns:
        Tuple[str, List[str], Dict[str, str]]: A tuple containing the problem description, constraints, and example code.
    """
    soup = BeautifulSoup(html, "html.parser")

    problem_description = []
    Constraints = []
    Cleaned = dict()

    p_tag = soup.find("p")
    try:
        while "Example" not in p_tag.get_text():
            problem_description.append(p_tag.get_text())
            p_tag = p_tag.find_next("p")
        problem_description = "\n".join(problem_description)
    except:
        problem_description = None

    p_tags = soup.find_all("p")
    for p_tag in p_tags:
        if "Constraints" in p_tag.get_text():
            p_tag_str = str(p_tag)
            p_tag_str = p_tag_str.replace("Constraints:", "")
            p_tag_str = p_tag_str.replace("<sup>", "**")
            p_tag_str = p_tag_str.replace("</sup>", "")
            p_tag_str = p_tag_str.replace("<br/>", "\n")
            p_tag = BeautifulSoup(p_tag_str, "html.parser")
            p_tag = p_tag.get_text().split("\n")
            Constraints = [constraint for constraint in p_tag if constraint]

    p_tag = soup.find("p", string=lambda text: text and "Example" in text)

    half_cleaned = dict()
    index = 1

    try:
        p_tags = soup.find_all("p")
        for p_tag in p_tags:
            if "example" in p_tag.get_text().lower():
                next_pre_tag = p_tag.find_next("pre")
                half_cleaned[f"Example {index}"] = next_pre_tag.get_text().strip()
                index += 1
    except:
        half_cleaned = None

    return problem_description, Constraints, half_cleaned

def upload_json_to_s3(s3_key: str, data: Dict) -> None:
    """
    Uploads the given JSON data to the given S3 key.

    Args:
        s3_key (str): The S3 key to upload the data to.
        data (Dict): The JSON data to upload.

    Returns:
        None
    """
    S3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, indent=4),
        ContentType='application/json'
    )
    logging.info(f"--UPLOADED : {s3_key}")

def get_objects_list(s3_key: str) -> List[str]:
    """
    This function retrieves a list of S3 objects that match the given S3 key.

    Args:
        s3_key (str): The S3 key to match the objects against.

    Returns:
        List[str]: A list of S3 object keys that match the given S3 key.
    """
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
    
if __name__ == '__main__':
    # Initialize global variables
    global_vars()
    # Initialize logging
    initialize_logging(LOG_FILE_DIR)

    with sync_playwright() as p:
        # Open a new browser using Playwright
        browser = p.chromium.launch(headless=HEADLESS_OPTION)
        context = browser.new_context()
        page = context.new_page()
        
        # Login to GeeksforGeeks
        login_to_gfg(page, GFG_MAIL_OR_USERNAME, GFG_PASSWORD)

        # Iterate through problem pages
        problem_index = 0
        while START_PAGE <= END_PAGE:
            # Get the problem list on the current page
            problem_list = get_problem_list(START_PAGE)
            # Iterate through the problems
            for problem in problem_list:
                
                problem_index += 1
                logging.info(f"PAGE --[{START_PAGE}]")
                logging.info(f"PROBLEM --[{problem_index}]")
                
                problem_data = dict()
                    
                problem_data['title'] = problem.get('problem_name')
                problem_data['title_slug'] = problem.get('slug')
                problem_data['difficulty'] = problem.get('difficulty')
                
                uploaded_list = get_objects_list(S3_FOLDER_PATH)
                s3_key = S3_FOLDER_PATH + '/' + problem_data.get("title_slug") + '.json'
                if s3_key in uploaded_list:
                    logging.info(f'CLOUD --> FILE ALREADY PRESENT {s3_key}')
                    continue

                source = dict()
                source['url'] = problem.get('problem_url')
                source['gfg_accuracy'] = problem.get('accuracy')
                source['gfg_question_id'] = problem.get('id')
                source['all_gfg_submissions'] = problem.get('all_submissions')
                source['problem_type'] = problem.get('problem_type')
                source['problem_level'] = problem.get('problem_level')
                source['gfg_marks'] = problem.get('marks')
                source['content_type'] = problem.get('content_type')
                source['visibility_type'] = problem.get('visibility_type')
                source['topic_order'] = problem.get('topic_order')
                problem_data['source'] = source

                problem_data['tags'] = problem.get('tags').get('topic_tags')

                problem_data['company_tags'] = problem.get('tags').get('company_tags')
                
                problem_meta, submission_100 = get_problem_data(problem_data.get('source').get('url'), problem_data.get('title_slug'), context, page)
                
                problem_data['problem_id'] = problem_meta.get('id')
                
                problem_data['html_content'] = get_problem_html(problem_data.get('source').get('url'))
                
                problem_description, Constraints, Cleaned = get_data_from_html(problem_data.get('html_content'))
        
                problem_data['problem_description'] = problem_description
                
                problem_data['constraints'] = Constraints
                
                problem_data['testcases'] = dict()
                
                problem_data['testcases']['formatted'] = problem_meta.get('extra').get('input')
                
                problem_data['testcases']['half_cleaned'] = Cleaned
                
                problem_data['available_languages'] = list(problem_meta.get('extra').get('problem_languages').keys())
                
                code_snippets = dict()
                driver_code = problem_meta.get('extra').get('initial_user_func')
                for key_lang in driver_code:
                    code = dict()
                    code_snippet = driver_code.get(key_lang)
                    code['initial_code'] = code_snippet.get('initial_code')
                    code['user_code'] = code_snippet.get('user_code')
                    code_snippets[key_lang] = code
                problem_data['code_snippets'] = code_snippets
                
                problem_data['user_solutions'] = submission_100
            
                upload_json_to_s3(s3_key, problem_data)
                
            START_PAGE += 1
                       
        context.close()     
        browser.close()
