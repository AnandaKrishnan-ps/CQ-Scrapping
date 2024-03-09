import boto3
import os
import logging
import time
import json
import sys
import requests
from playwright.sync_api import sync_playwright
from playwright.sync_api import Page, BrowserContext, Browser
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
import re
import jsbeautifier
import httpx

def global_vars():
    """
    This function initializes global variables used throughout the code.
    """
    #GFG -- CREDENTIALS
    global MAIL_OR_USERNAME, PASSWORD
    MAIL_OR_USERNAME    = "your_email@example.com"
    PASSWORD            = "YourPasswordHere"

    #OFFSETS
    global START_PAGE, END_PAGE
    START_PAGE  = 0
    END_PAGE    = 745
    
    #AWS
    global S3, S3_FOLDER_PATH, BUCKET
    AWS_ACCESS_KEY  = "YourAccessKeyHere"
    AWS_SECRET_KEY  = "YourSecretKeyHere"
    AWS_REGION      = "YourRegionHere"
    BUCKET          = "YourBucketNameHere"
    S3 = boto3.client(
        's3', 
        aws_access_key_id       = AWS_ACCESS_KEY, 
        aws_secret_access_key   = AWS_SECRET_KEY, 
        region_name             = AWS_REGION
        )
    S3_FOLDER_PATH              = "YourFolderPathHere"
    
    #LOGGING
    global LOG_FILE_DIR
    LOG_FILE_DIR = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.path.basename(os.path.abspath(__file__)).replace('.py', '.log')
        )
    
    #HEADERS
    global HINT_RESPONSE, URL
    HINT_RESPONSE = dict()
    SLUG = None

def initialize_logging():
    """
    This function initializes the logging system.
    """
    # Get the root logger
    logger = logging.getLogger()

    # Set the log level to INFO
    logger.setLevel(logging.INFO)

    # Create a log message format
    formatter = logging.Formatter('%(asctime)s -- %(message)s', '%Y-%m-%d %H:%M:%S')

    # Create a file handler and set the formatter
    file_handler = logging.FileHandler(LOG_FILE_DIR)
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    # Create a stream handler and set the formatter
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # Add the stream handler to the logger
    logger.addHandler(stream_handler)

    # Log a message to the console and the log file
    logging.info('LOCAL   --> INITIALIZED LOGGING FILE')
    logging.info('------------------------------------NEW LOG----------------------------------\n\n')

def do_login() -> Tuple[Page, BrowserContext, Browser]:
    """
    This function launches a browser, creates a new page and context, and navigates to the InterviewBit sign-in page.
    It then enters the email address and password, and submits the login form.
    Returns a tuple containing the page, context, and browser objects.
    """
    logging.info("BROWSER --> LAUNCHNING BROWSER")
    browser = p.chromium.launch(headless=False)

    logging.info('BROWSER --> CREATING A NEW PAGE & CONTEXT')
    context = browser.new_context()
    page = context.new_page()

    logging.info('BROWSER --> REDIRECTING TO INTERVIEWBIT SIGN IN')
    page.goto("https://www.interviewbit.com/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Sign in", exact=True).click()
    page.locator("div:nth-child(4) >.tappable").click()

    logging.info(f'BROWSER --> ENTERING MAIL           <MAIL = {MAIL_OR_USERNAME}>')
    page.get_by_placeholder("@xyz.com").click()
    page.get_by_placeholder("@xyz.com").press_sequentially(MAIL_OR_USERNAME)

    logging.info('BROWSER --> WAIT FOR RECAPTCHA BOX  <TIME = 3 SECONDS>')
    page.wait_for_timeout(3000)
    try:
        iframe = page.query_selector("iframe")
        iframe_name = iframe.get_attribute("name")
        page.frame_locator(f"iframe[name=\"{iframe_name}\"]").get_by_label("I'm not a robot").click()
        page.wait_for_timeout(3000)
        is_captcha_checked = page.frame_locator(f"iframe[name=\"{iframe_name}\"]").get_by_label("I'm not a robot").is_checked()
        if not is_captcha_checked:
            logging.info('BROWSER --> WAIT FOR CAPTCHA RESOLVE<TIME = 15 SECONDS>')
            page.wait_for_timeout(15000)
    except Exception as e:
        logging.info(f"BROWSER --> EXCEPTION OCCURED       <EXCEPTION = {e}>")

    logging.info('BROWSER --> REDIRECTING TO PASSWORD PAGE')
    logging.info(f'BROWSER --> TYPING PASSWORD         <PASSWORD> = {"*"*len(PASSWORD)}>')
    page.get_by_text("Continue", exact=True).click()
    page.locator("#password-field").click()
    page.locator("#password-field").press_sequentially(PASSWORD)
    page.get_by_text("Proceed").click()

    return page, context, browser

def get_problem_list(page_offset: int) -> List[Dict]:
    """
    This function gets the problem list from the InterviewBit API.

    Args:
        page_offset (int): The page offset of the problem list.

    Returns:
        List[Dict]: A list of problem dictionaries.
    """
    logging.info(f'API     --> GETTING PROBLEM LIST    <PAGE OFFSET = {page_offset}>')
    url = f"https://www.interviewbit.com/v2/problem_list/?&page_offset={page_offset}&page_limit=20"
    response = requests.request("GET", url)
    return response.json().get('items')

def get_objects_list(s3_key: str) -> List[str]:
    """
    This function gets a list of objects in an S3 bucket.

    Args:
        s3_key (str): The S3 key of the folder to get the objects from.

    Returns:
        List[str]: A list of objects in the S3 bucket.
    """
    logging.info(f"CLOUD   --> GETTING OBJECTS IN S3   <S3 PATH = |{s3_key}|>")

    object_list: List[str] = []
    continuation_token: Optional[str] = None

    while True:
        if continuation_token:
            response: Dict = S3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=s3_key,
                ContinuationToken=continuation_token
            )
        else:
            response: Dict = S3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=s3_key
            )
        if "Contents" in response:
            for obj in response["Contents"]:
                object_list.append(obj["Key"])
        if not response.get("IsTruncated"):
            break
        continuation_token = response["NextContinuationToken"]

    return object_list[1:]

def upload_json_to_s3(s3_key: str, data: Dict) -> None:
    """
    Uploads a Dict object to an S3 bucket as a JSON file.

    Args:
        s3_key (str): The S3 key of the file to upload.
        data (Dict): The JSON object to upload.

    Returns:
        None

    """
    S3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, indent=4),
        ContentType='application/json'
    )
    logging.info(f"CLOUD   --> UPLOADED FILE           <S3 KEY = |{s3_key}|>")

def get_object_as_json(s3_key: str) -> Dict:
    """
    This function retrieves an object from an S3 bucket as a JSON file.

    Args:
        s3_key (str): The S3 key of the object to retrieve.

    Returns:
        Dict: The JSON object.
    """
    response = S3.get_object(Bucket=BUCKET, Key=s3_key)
    json_string = response['Body'].read().decode('utf-8')
    json_data = json.loads(json_string)
    return json_data

def get_problem_data(slug: str) -> Dict:
    """
    This function retrieves the problem data from the InterviewBit API.

    Args:
        slug (str): The problem slug.

    Returns:
        Dict: The problem data.
    """
    logging.info(f'API     --> GETTING PROBLEM DATA    <SLUG = {slug}>')
    url = f"https://www.interviewbit.com/problems/{slug}/"
    response = requests.request('GET', url)
    if response.status_code != 200:
        return
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tag = soup.find('script', text=lambda text: text and 'window.__INTERVIEWBIT__.problemsData' in text)
    code = script_tag.string
    beautified_code = jsbeautifier.beautify(code)
    match = re.search(r'window\.__INTERVIEWBIT__\.problemsData\s*=\s*({.*?});', beautified_code, re.DOTALL)
    problems_data_json = match.group(1)
    problems_data = json.loads(problems_data_json)
    return problems_data

def playwright_request_handler(response):
    """
    This function sets the global variable "HEADERS" with the values of the request headers "accept-language", "cookie", and "user-agent".

    Parameters:
        request (Request): The Playwright request object.

    Returns:
        None
    """
    global HINT_RESPONSE, SLUG
    try:
        if response.url and f'https://www.interviewbit.com/v2/problems/{SLUG}/hints' in str(response.url) and response.status == 200:
            HINT_RESPONSE[f"{response.url}"] = response.json()
            logging.info(f"NETWORK --> CAPTURED RESPONSE       <URL = {response.url}>")
    except:
        pass
    
def open_api_gateways(page):
    """
    Opens the API gateways for the given problem slug.

    Args:
        page (Page): The Playwright page object.

    Returns:
        None
    """
    global SLUG
    problem_url = f"https://www.interviewbit.com/problems/{SLUG}"
    page.on("response", playwright_request_handler)
    page.goto(problem_url, wait_until="domcontentloaded")

    # Click on the Hints link
    try:
        page.get_by_role("link", name="Hints").click(timeout=5000)
    except Exception as e:
        logging.info(f"BROWSER --> EXCEPTION OCCURED       <EXCEPTION = {e}>")
    page.wait_for_timeout(2500)

    # Click on the Unlock Hint button
    try:
        page.get_by_text("Unlock Hint").click(timeout=5000)
    except Exception as e:
        logging.info(f"BROWSER --> EXCEPTION OCCURED       <EXCEPTION = {e}>")

    # Click on the Solution Approach link
    try:
        page.locator("a").filter(has_text="Solution Approach").click()
    except Exception as e:
        logging.info(f"BROWSER --> EXCEPTION OCCURED       <EXCEPTION = {e}>")
    page.wait_for_timeout(2500)

    # Click on the Unlock Solution Approach button
    try:
        page.get_by_text("Unlock Solution Approach").click(timeout=5000)
    except Exception as e:
        logging.info(f"BROWSER --> EXCEPTION OCCURED       <EXCEPTION = {e}>")

    # Click on the Complete Solution link
    try:
        page.locator("a").filter(has_text="Complete Solution").click()
    except Exception as e:
        logging.info(f"BROWSER --> EXCEPTION OCCURED       <EXCEPTION = {e}>")
    page.wait_for_timeout(2500)

    # Click on the Unlock Complete Solution button
    try:
        page.get_by_text("Unlock Complete Solution").click(timeout=5000)
    except Exception as e:
        logging.info(f"BROWSER --> EXCEPTION OCCURED       <EXCEPTION = {e}>")
        
def get_hints(hints_meta, slug: str, page: Page) -> None:
    """
    Opens the API gateways for the given problem slug.

    Args:
        slug (str): The problem slug.
        page (Page): The Playwright page object.

    Returns:
        None
    """
    
    hints_dict = dict()
    hint_id = None
    solution_approach_id = None
    complete_solution_id = None
    
    if hints_meta is None:
        return None
    
    global URL
    global HINT_RESPONSE
    
    for hint in hints_meta:
        if 'hint' in hint.get('title').lower():
            hint_id = hint.get('id')
        if 'approach' in hint.get('title').lower():
            solution_approach_id = hint.get('id')
        if 'complete' in hint.get('title').lower():
            complete_solution_id = hint.get('id')
                
    open_api_gateways(page)
    logging.info(f"PAGE    --> RESPONSE CAPTURE WAIT    <TIME = 25 SECONDS>")
    page.wait_for_timeout(25000)
    
    try:
        hint_url = [url for url in HINT_RESPONSE if f"hints/{hint_id}" in url].pop(0)
        hints_dict['hint'] = HINT_RESPONSE.get(hint_url).get('hint').get('markdown_content')
    except:
        hints_dict['hint'] = None
        
    try:
        approach_url = [url for url in HINT_RESPONSE if f"hints/{solution_approach_id}" in url].pop(0)
        hints_dict['solution_approach'] = HINT_RESPONSE.get(approach_url).get('hint').get('markdown_content')
    except:
        hints_dict['solution_approach'] = None
    
    try:
        solution_url = [url for url in HINT_RESPONSE if f"hints/{complete_solution_id}" in url].pop(0)
        solution_response = HINT_RESPONSE.get(solution_url).get('hint').get('complete_solution')
        languages = solution_response.get('language_names')
        editorial_solutions = solution_response.get('editorial_solutions')
        hints_dict['solutions'] = dict()
        for language_id in languages:
            if language_id not in editorial_solutions:
                continue
            html_solution = editorial_solutions.get(language_id).get('content')
            div_element = BeautifulSoup(html_solution, 'html.parser').find('div')
            if div_element is None:
                hints_dict['solutions'][languages.get(language_id)] = html_solution
            else:    
                actual_solution = div_element.get_text().strip()
                hints_dict['solutions'][languages.get(language_id)] = actual_solution
    except:
        hints_dict['solutions'] = None
            
    page.remove_listener("response", playwright_request_handler)
    HINT_RESPONSE = dict()
    
    return hints_dict

def get_code_snippets(slug: str, languages: Dict) -> Dict:
    """
    This function retrieves the code snippets for the given problem slug and programming languages.

    Args:
        slug (str): The problem slug.
        languages (Dict): A dictionary of programming languages with their IDs as keys and language names as values.

    Returns:
        Dict: A dictionary of programming languages with their code snippets as values.
    """
    code_snippets = dict()
    for language_id in languages:
        url = f"https://www.interviewbit.com/v2/problems/{slug}/codes/?programming_language_id={language_id}"
        """
        This function uses the requests library to make an HTTP GET request to the InterviewBit API endpoint
        that returns the code snippet for the specified problem slug and programming language.
        """
        logging.info(f'API     --> GETTING CODE SNIPPET    <LANGUAGE = {languages.get(language_id)}>')
        code_snippet = requests.get(url).json().get('content')
        code_snippets[languages.get(language_id)] = code_snippet
    return code_snippets

if __name__ == '__main__':
    
    global_vars()
    initialize_logging()
    
    with sync_playwright() as p:
        
        page, context, browser = do_login()
        
        while START_PAGE <= END_PAGE:
            
            problem_list = get_problem_list(START_PAGE)
            global SLUG
                        
            for problem in problem_list: 
                
                # Skipping the puzzle MCQs
                if problem.get('topic_title') == 'Puzzles':
                    continue
                
                uploaded_list = get_objects_list(S3_FOLDER_PATH)
                s3_key = S3_FOLDER_PATH + '/' + problem.get('slug')
                if s3_key in uploaded_list:
                    logging.info(f'CLOUD   --> FILE ALREADY PRESENT    <FILE = |{s3_key}|>')
                    uploaded_json = get_object_as_json(s3_key)
                    if not(uploaded_json.get('hint') is None or uploaded_json.get('solution_approach') is None or uploaded_json.get('solutions') is None):
                        continue
                
                problem_data = dict()
                
                problem_data['title'] = problem.get('problem_statement')
                problem_data['title_slug'] = problem.get('slug')
                problem_data['difficulty'] = problem.get('difficulty_level')
                problem_data['company_tags'] = problem.get('tags')
                problem_data['category'] = problem.get('topic_title')
                
                SLUG = problem.get('slug')
                
                source = dict()
                source['url'] = f"https://www.interviewbit.com/problems/{SLUG}"
                source['interviewbit_score'] = problem.get('score')
                source['interviewbit_avg_solving_time'] = problem.get('average_solving_time')
                source['interviewbit_solved_count'] = problem.get('solved_by')
                
                problem_data['source'] = source
                
                problem_content = get_problem_data(SLUG)
                
                if problem_content is None:
                    continue
                
                languages = problem_content.get('meta').get('languages')
                
                available_languages = languages.values()
                problem_content['available_languages'] = list(available_languages)
                problem_data['code_snippets'] = get_code_snippets(SLUG, languages)
                problem_data['input_descriptor'] = problem_content.get('meta').get('input_descriptor')
                problem_data['html_content'] = problem_content.get('meta').get('markdown_content')
                
                html_soup = BeautifulSoup(problem_data['html_content'], 'html.parser')
                
                try:
                    div_ele = html_soup.find('div', id='problem_description_markdown_content_value')
                    description = div_ele.get_text().strip()
                    problem_data['description'] = description
                except:
                    problem_data['description'] = None
                
                try:
                    div_ele = html_soup.find('div', id='problem_constraints_markdown_content_value')
                    constraints = div_ele.get_text().strip().split("\n")
                    problem_data['constraints'] = constraints
                except:
                    problem_data['constraints'] = None
                
                try:
                    div_ele = html_soup.find('div', id='input_format_markdown_content_value')
                    input_format = div_ele.get_text().strip()
                    problem_data['input_format'] = input_format
                except:
                    problem_data['input_format'] = None
                
                try:
                    div_ele = html_soup.find('div', id='output_format_markdown_content_value')
                    output_format = div_ele.get_text().strip()
                    problem_data['output_format'] = output_format
                except:
                    problem_data['output_format'] = None
                
                try:
                    div_ele = html_soup.find('div', id='example_input_markdown_content_value')
                    p_tags = div_ele.find_all('p')
                    inputs = dict()
                    for tag in p_tags:
                        key = tag.get_text().strip()
                        pre_tag = tag.find_next_sibling('pre')
                        value = pre_tag.get_text().strip()
                        inputs[key] = value
                    problem_data['example_input'] = inputs
                except:
                    problem_data['example_input'] = None
                
                try:
                    div_ele = html_soup.find('div', id='example_output_markdown_content_value')
                    p_tags = div_ele.find_all('p')
                    p_tags = [p for p in p_tags if p.get_text().strip()]
                    outputs = dict()
                    for tag in p_tags:
                        key = tag.get_text().strip()
                        pre_tag = tag.find_next_sibling('pre')
                        value = pre_tag.get_text().strip()
                        outputs[key] = value
                    problem_content['example_output'] = outputs
                except:
                    problem_content['example_output'] = None
                
                try:
                    div_ele = html_soup.find('div', id='example_explanation_markdown_content_value')
                    p_tags = div_ele.find_all('p')
                    p_tags = [p for p in p_tags if p.get_text().strip()]
                    explanations = dict()
                    for tag in p_tags:
                        key = tag.get_text().strip()
                        pre_tag = tag.find_next_sibling('pre')
                        value = pre_tag.get_text().strip()
                        explanations[key] = value
                    problem_content['example_explanation'] = explanations
                except:
                    problem_content['example_explanation'] = None
                
                hints_meta = problem_content.get('hints').get('hints')
                
                problem_data['hints_meta'] = hints_meta
                
                hints_dict = get_hints(hints_meta, SLUG, page)
                
                if hints_dict is not None:
                    for key in hints_dict:
                        problem_data[key] = hints_dict.get(key)
                                    
                # with open(f'sample/{problem_data.get("title_slug")}.json', 'w')   # test
                #     json.dump(problem_data, file, indent=4)
                                    
                upload_json_to_s3(s3_key, problem_data) # src
            
            START_PAGE += 1
        
        context.close()
        browser.close()
