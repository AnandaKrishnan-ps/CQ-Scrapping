import logging
import sys
import os
import boto3
import json
import requests
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# type hinting imports
from playwright.sync_api import Page
from typing import List, Dict, Tuple, Optional, Union, Any

def constants_definitions() -> None:
    """
    Define global constants used in the script.
    """
    # BROWSER
    global HEADLESS_OPTION
    HEADLESS_OPTION = True

    # AWS
    global S3, S3_FOLDER_PATH, BUCKET
    AWS_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY"
    AWS_SECRET_KEY = "YOUR_AWS_SECRET_KEY"
    AWS_REGION = "YOUR_AWS_REGION"
    BUCKET = "YOUR_BUCKET"
    S3 = boto3.client(
        's3', 
        aws_access_key_id=AWS_ACCESS_KEY, 
        aws_secret_access_key=AWS_SECRET_KEY, 
        region_name=AWS_REGION
    )
    S3_FOLDER_PATH = "YOUR_S3_LOCATION"
    
    # LOGGING
    global LOG_FILE_DIR
    global LOCAL_LOG, TEST_LOG, BROWSER_LOG, API_LOG, CLOUD_LOG
    LOG_FILE_DIR = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.path.basename(os.path.abspath(__file__)).replace('.py', '.log')
    )
    LOCAL_LOG = "LOCAL"
    TEST_LOG = "TEST\n\n"
    BROWSER_LOG = "BROWSER"
    API_LOG = "API"
    CLOUD_LOG = "CLOUD"

def log(log: str, *message: Tuple[str]) -> None:
    """
    Log messages to the console and file.

    Parameters:
        log (str): The type of log (e.g., LOCAL, TEST, BROWSER, API, CLOUD).
        message (Tuple[str]): The messages to be logged.
    """
    message = list(map(str, message))
    message[0] = message[0].upper()
    logging.info(f"{log.ljust(9)} --> {' -- '.join(message)}")

def initialize_logging(log_file_dir: str) -> None:
    """
    Initialize logging settings.

    Parameters:
        log_file_dir (str): The directory path for the log file.
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
    
    logging.info('\n\n------------------------------------NEW LOG----------------------------------\n\n')

def get_objects_list(s3_key: str) -> List[str]:
    """
    Get a list of objects in an S3 bucket with a given prefix.

    Parameters:
        s3_key (str): The prefix/key for filtering objects in the S3 bucket.

    Returns:
        List[str]: A list of object keys.
    """
    log(CLOUD_LOG, "getting objects in", s3_key)

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
    Upload JSON data to an S3 bucket.

    Parameters:
        s3_key (str): The key under which the object is stored in the bucket.
        data (Dict): The JSON data to be uploaded.
    """
    S3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, indent=4),
        ContentType='application/json'
    )
    log(CLOUD_LOG, "uploading json to s3", s3_key)

def get_problem_urls(page: Page) -> List[str]:
    """
    Get the URLs of problems from the main page.

    Parameters:
        page (Page): The Playwright page object.

    Returns:
        List[str]: A list of problem URLs.
    """
    main_url = "https://www.techiedelight.com"
    log(BROWSER_LOG, f"redirecting to", main_url)
    page.goto(main_url)
    
    log(BROWSER_LOG, "fetching page content")
    content = page.content()
    
    log(LOCAL_LOG, "getting problem urls")
    
    soup = BeautifulSoup(content, 'html.parser')
    problem_list_span_tag = soup.find('span', id="problemsList")
    ol_sibling_tag = problem_list_span_tag.find('ol')
    li_tag_list = ol_sibling_tag.find_all('li')
    
    problem_url_list = list()
    for li_tag in li_tag_list:
        a_tag = li_tag.find('a')
        problem_param = a_tag.get('href')
        problem_url = f"{main_url}{problem_param}"
        problem_url_list.append(problem_url)
    
    log(LOCAL_LOG, "returning problem urls")
    
    return problem_url_list

def get_slug(problem_url: str) -> str:
    """
    Extract the slug from a problem URL.

    Parameters:
        problem_url (str): The URL of the problem.

    Returns:
        str: The slug extracted from the URL.
    """
    _, params = problem_url.split('?')
    slug = params.split('=')[-1].strip()
    return slug

def get_code(slug: str, language: str) -> str:
    """
    Get code for a given problem slug and programming language.

    Parameters:
        slug (str): The slug of the problem.
        language (str): The programming language (e.g., "cpp", "py", "java").

    Returns:
        str: The code snippet.
    """
    url = f"https://www.techiedelight.com/practice/template/{slug}/{slug}.{language}"
    payload = {}
    headers = {
        'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Accept': '*/*',
        'Referer': f'https://www.techiedelight.com/?problem={slug}',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    return response.text

def fetch_code_snippet(slug: str) -> Dict[str, str]:
    """
    Fetch code snippets for a given problem slug.

    Parameters:
        slug (str): The slug of the problem.

    Returns:
        Dict[str, str]: A dictionary containing code snippets for different programming languages.
    """
    cpp_code = get_code(slug, "cpp")
    py_code = get_code(slug, "py")
    java_code = get_code(slug, "java")
    code_snippets = {
        'cpp': cpp_code,
        'python': py_code,
        'java': java_code,
    }
    return code_snippets

def remove_css(html_content : str) -> str:
    """
    Remove CSS styles from an HTML document.

    Parameters:
        html_content (str): The HTML document as a string.

    Returns:
        str: The HTML document with all the CSS styles removed.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for style_tag in soup.find_all('style'):
        style_tag.decompose()

    for tag in soup.find_all():
        del tag['style']
    
    return str(soup)

def fetch_html_and_editorial_url(page: Page, problem_url: str) -> str:
    """
    Fetch HTML content and editorial URL for a given problem URL.

    Parameters:
        page (Page): The Playwright page object.
        problem_url (str): The URL of the problem.

    Returns:
        Tuple[str, str]: A tuple containing the editorial URL and HTML content.
    """
    log(BROWSER_LOG, "redirecting to", problem_url)
    main_url = "https://www.techiedelight.com"
    page.goto(problem_url)
    html_text = page.content()
    soup = BeautifulSoup(html_text, 'html.parser')
    a_tag = soup.find('a', id="editorial")
    editorial_href = a_tag.get('href')
    editorial_url = main_url + editorial_href 
    html_text = remove_css(html_text)
    return (
        editorial_url, 
        html_text
    )

def fetch_dirty_testcases(slug: str) -> str:
    """
    Fetch dirty test cases for a given problem slug.

    Parameters:
        slug (str): The slug of the problem.

    Returns:
        str: The dirty test cases.
    """
    log(API_LOG, "fetching testcases", slug)
    url = f"https://www.techiedelight.com/practice/template/{slug}/{slug}"
    payload = {}
    headers = {
        'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Accept': '*/*',
        'Referer': f'https://www.techiedelight.com/?problem={slug}',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    return response.text

def custom_clean(dirty_x: str) -> Union[bool, int, str, List]:
    """
    Clean dirty input data.

    Parameters:
        dirty_x (str): The dirty input data.

    Returns:
        Union[bool, int, str, List]: The cleaned data.
    """
    if ',' in dirty_x:
        try:
            return list(map(int, dirty_x.split(',')))
        except:
            return dirty_x.split(',')
    
    elif 'Y' in dirty_x.upper():
        x = dirty_x.replace('Y', 'True')
        x = x.replace('y', 'true')
        try:
            return eval(x)
        except:
            return dirty_x
    
    elif 'N' in dirty_x.upper():
        x = dirty_x.replace('N', 'False')
        x = x.replace('n', 'False')
        try:
            x = eval(x)
            return x
        except:
            return dirty_x
    
    else:
        try:
            return int(dirty_x)
        except:
            return dirty_x

def clean_testcases(dirty_content: str) -> List[Dict[str, Union[bool, int, str, List]]]:
    """
    Clean dirty test cases.

    Parameters:
        dirty_content (str): The dirty test cases.

    Returns:
        List[Dict[str, Union[bool, int, str, List]]]: The cleaned test cases.
    """
    dirty_testcases_list = dirty_content.split('\n')
    cleaned_testcases = list()
    for dirty_TC in dirty_testcases_list:
        dirty_TC = dirty_TC.split('|')
        dirty_TC = list(map(str.strip, dirty_TC))
        inputs, outputs = dirty_TC[:-1], dirty_TC[-1]
        inputs = list(map(custom_clean, inputs))
        if type(inputs) == list:
            inputs = inputs[0] if len(inputs) == 1 else inputs
        if '#' in outputs:
            outputs = outputs.split('#')
        if type(outputs) == list:
            outputs = list(map(lambda x: x.strip(), outputs))
        else:
            outputs = outputs.strip()
        if type(outputs) == list:
            outputs = list(map(custom_clean, outputs))
        else:
            outputs = custom_clean(outputs)
        
        if type(outputs) == list:
            outputs = outputs[0] if len(outputs) == 1 else outputs
        cleaned_testcases.append({
            'input': inputs,
            'accepted_output(s)': outputs
        })
    return cleaned_testcases
    
def fetch_testcases(slug: str) -> Dict[str, str]:
    """
    Fetch test cases for a given problem slug.

    Parameters:
        slug (str): The slug of the problem.

    Returns:
        Dict[str, str]: A dictionary containing dirty and cleaned test cases.
    """
    dirty_testcases = fetch_dirty_testcases(slug)
    cleaned_testcases = clean_testcases(dirty_testcases)
    return {
        'dirty': dirty_testcases,
        'cleaned': cleaned_testcases
    }

def fetch_editorial_solutions(page: Page, editorial_url: str) -> Dict[str,List[str]]:
    """
    Fetch editorial solutions for a given problem.

    Parameters:
        page (Page): The Playwright page object.
        editorial_url (str): The URL of the editorial page.

    Returns:
        Dict[str,List[str]]: Editorial solutions.
    """
    log(BROWSER_LOG, "redirecting to editorial url", editorial_url)
    page.goto(editorial_url, wait_until='domcontentloaded')
    editorial_content = page.content()
    editorial_content = BeautifulSoup(editorial_content, 'html.parser')
        
    h2_tags_list = editorial_content.find_all('h2', class_='tabtitle responsive-tabs__heading')
    h2_tags_list.extend(editorial_content.find_all('h2', class_='tabtitle responsive-tabs__heading responsive-tabs__heading--active'))
    
    test_dict = dict()
    
    for h2_tag in h2_tags_list:
        
        language = h2_tag.text.strip().lower()
        
        div_tag = h2_tag.find_next('div', class_='c-pre')
        code = div_tag.text
        
        if language not in test_dict:
            test_dict[language] = list()
            test_dict[language].append(code)
        else:
            test_dict[language].append(code)
        
    return test_dict

if __name__ == '__main__':

    constants_definitions()
    initialize_logging(LOG_FILE_DIR)
    
    with sync_playwright() as playwright:
        
        log(BROWSER_LOG, "launching browser")
        
        browser = playwright.chromium.launch(headless=HEADLESS_OPTION)
        context = browser.new_context()
        page = context.new_page()
        
        problem_number = 0
        problem_urls = get_problem_urls(page)
        
        log(LOCAL_LOG, f'{"-"*30}\n')
        
        for problem_url in problem_urls:
            
            start_time = time.time()
            
            problem_data = dict()
            
            log(API_LOG, "going through", problem_url)
            
            slug = get_slug(problem_url)
            
            uploaded_list = get_objects_list(S3_FOLDER_PATH)
            s3_key = f"{S3_FOLDER_PATH}/{slug}.json"
            if s3_key in uploaded_list:
                log(CLOUD_LOG, "file already present in", s3_key)
                log(LOCAL_LOG, "PROBLEM NUMBER", f"[{problem_number}]")
                log(LOCAL_LOG, f'{"-"*30}\n')
                
                problem_number += 1
                continue
            
            code_snippets = fetch_code_snippet(slug)
            editorial_url, html_content = fetch_html_and_editorial_url(page, problem_url)
            sample_code_snippet = code_snippets.get('python')
            testcases = fetch_testcases(slug)
            editorial_solutions = fetch_editorial_solutions(page, editorial_url)
            
            problem_data['slug'] = slug
            problem_data['url'] = problem_url
            problem_data['code_snippets'] = code_snippets
            problem_data['html'] = html_content
            
            problem_data['testcases'] = testcases
            
            problem_data['editorial_url'] = editorial_url
            problem_data['editorial_solutions'] = editorial_solutions
            
            upload_json_to_s3(s3_key, problem_data)
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            
            log(LOCAL_LOG, "completed uploading in", f"{minutes} MINS {seconds} SECS")
            log(LOCAL_LOG, "PROBLEM NUMBER", f"[{problem_number}]")
            log(LOCAL_LOG, f'{"-"*30}\n')
            
            problem_number += 1