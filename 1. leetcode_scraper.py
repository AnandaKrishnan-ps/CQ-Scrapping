import requests
import json
from bs4 import BeautifulSoup
import time
import logging
import sys
from logging.handlers import RotatingFileHandler
import boto3

# Define the range for fetching questions
start_offset = 0
end_offset = 3060
total_offset = 3060

# Function to fetch list of questions from LeetCode
def get_questions_list(skip: int = 0) -> list[dict]:
    """
    Fetches a list of questions from LeetCode API.

    Args:
        skip (int): Number of questions to skip.

    Returns:
        list[dict]: List of questions.
    """
    # API endpoint URL
    url = "https://leetcode.com/graphql/"
    # Payload for GraphQL query
    payload = "{\"query\":\"\\n    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {\\n  problemsetQuestionList: questionList(\\n    categorySlug: $categorySlug\\n    limit: $limit\\n    skip: $skip\\n    filters: $filters\\n  ) {\\n    total: totalNum\\n    questions: data {\\n      acRate\\n      difficulty\\n      likes\\n      dislikes\\n      freqBar\\n      frontendQuestionId\\n      isFavor\\n      paidOnly\\n      status\\n      title\\n      titleSlug\\n      topicTags {\\n        name\\n        id\\n        slug\\n      }\\n      hasSolution\\n      hasVideoSolution\\n    }\\n  }\\n}\\n    \",\"variables\":{\"categorySlug\":\"all-code-essentials\",\"skip\":"+str(skip)+",\"limit\":50,\"filters\":{}}}"
    # Making POST request to API
    response = requests.request(
        "POST", url, headers={'content-type': 'application/json'}, data=payload)
    # Parsing JSON response and returning list of questions
    return response.json().get('data').get('problemsetQuestionList').get('questions')

# Function to fetch content of a specific question from LeetCode
def get_question_content(title_slug):
    """
    Fetches content of a specific question from LeetCode.

    Args:
        title_slug (str): Slug of the question.

    Returns:
        dict: Question content.
    """
    # API endpoint URL
    url = 'https://leetcode.com/graphql/'
    # Payload for GraphQL query
    data = {
        "query": "query consolePanelConfig($titleSlug: String!) { question(titleSlug: $titleSlug) { exampleTestcaseList metaData content mysqlSchemas dataSchemas codeSnippets { langSlug code } envInfo topicTags { slug } companyTagStats hints stats } }",
        "variables": {"titleSlug": title_slug},
        "operationName": "consolePanelConfig"
    }
    # Making POST request to API
    response = requests.post(url, json=data, headers={'content-type': 'application/json'})
    # Parsing JSON response and returning question content
    return response.json().get('data').get('question')

# Function to upload JSON data to S3 bucket
def upload_json_to_s3(s3_key, data):
    """
    Uploads JSON data to an S3 bucket.

    Args:
        s3_key (str): Key for the object in S3 bucket.
        data (dict): JSON data to be uploaded.
    """
    # Implement your S3 upload logic here
    pass

# Function to initialize logging
def initialize_logging(log_file_dir):
    """
    Initializes logging configuration.

    Args:
        log_file_dir (str): Path to log file.
    """
    # Configuring logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s -- %(message)s')
    # Configuring file handler for logging
    file_handler = RotatingFileHandler(log_file_dir)
    file_handler.setFormatter(formatter)
    # Configuring stream handler for logging
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    # Adding handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    # Logging new log session
    logging.info('\n------------------------------------NEW LOG----------------------------------\n')

# Function to fetch list of objects from S3 bucket
def get_objects_list(s3_key):
    """
    Fetches list of objects from an S3 bucket.

    Args:
        s3_key (str): Key for the objects in S3 bucket.

    Returns:
        list[str]: List of object keys.
    """
    # Implement your S3 list objects logic here
    pass

# Function to fetch JSON object from S3 bucket
def get_object_as_json(s3_key):
    """
    Fetches a JSON object from an S3 bucket.

    Args:
        s3_key (str): Key for the object in S3 bucket.

    Returns:
        dict: JSON object.
    """
    # Implement your S3 get object logic here
    pass

# Main function
if __name__ == "__main__":

    # Define initial skip value
    skip = 0

    # AWS S3 configurations
    # Replace with your AWS credentials and region
    AWS_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY"
    AWS_SECRET_KEY = "YOUR_AWS_SECRET_KEY"
    AWS_REGION = "YOUR_AWS_REGION"
    BUCKET = "YOUR_S3_BUCKET_NAME"

    # Initialize S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )

    # Log file directory
    LOG_FILE_DIR = "YOUR_LOG_FILE_DIRECTORY"

    # Initialize logging
    initialize_logging(LOG_FILE_DIR)

    # Fetch list of uploaded objects from S3 bucket
    uploaded_list = get_objects_list("CQ-Scrapping/leetcode/new_upload/")

    # Check end offset
    if end_offset > total_offset:
        end_offset = total_offset

    # Initialize skip value
    skip = start_offset

    # Loop through question offsets
    while skip <= end_offset:

        # Retry loop for fetching questions
        for _ in range(1, 4):
            try:
                # Fetch questions
                logging.info(f"GET --> QUESTIONS FROM {skip}")
                questions = get_questions_list(skip)
                if questions == []:
                    break
            except:
                continue
            else:
                break

        # Retry loop for main execution
        for _ in range(1, 4):
            logging.info('TRY : {_}')
            try:
                # Iterate through questions
                for question in questions:

                    start_time = time.time()

                    # Initialize problem data dictionary
                    problem_data = dict()

                    # Extract relevant question data
                    problem_data['title'] = question.get('title')
                    problem_data['title_slug'] = question.get('titleSlug')
                    problem_data['difficulty'] = question.get('difficulty')

                    # Fetch question content
                    question_data = get_question_content(
                        problem_data['title_slug'])

                    # Process question data and upload to S3 bucket
                    # Implement your processing logic here

                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    minutes = int(elapsed_time // 60)
                    seconds = int(elapsed_time % 60)

                    logging.info(
                        f"COMPLETED : {problem_data['source']['leetcode_question_id']}. {problem_data['title']} in {minutes} minutes {seconds} seconds")

                    upload_json_to_s3(
                        f"CQ-Scrapping/leetcode/new_upload/{problem_data['source']['leetcode_question_id']}_{problem_data['title_slug']}.json", problem_data)

                    uploaded_list = get_objects_list(
                        "CQ-Scrapping/leetcode/new_upload/")
            except:
                continue
            else:
                break

        # Increment skip value for next iteration
        skip += 50
