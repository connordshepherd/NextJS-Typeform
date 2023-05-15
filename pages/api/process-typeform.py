print("Running process-typeform.py...")

from http.server import BaseHTTPRequestHandler
import os
import json
import requests
import re
from langchain import PromptTemplate
from langchain.llms import OpenAIChat
from typing import Tuple
from http import HTTPStatus

openaichat = OpenAIChat(model_name="gpt-3.5-turbo")
BASEPLATE_API_KEY = os.getenv('BASEPLATE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def query_vector_database(value):
    url = "https://app.baseplate.ai/api/datasets/81699ec2-d00f-4188-932d-00a9e89d14f6/search"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BASEPLATE_API_KEY}"
    }

    data = {
        "query": value,
        "top_k": 15,
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

def query_provider_database(value, care_type, zip_codes):
    url = "https://app.baseplate.ai/api/datasets/a7704a6a-3030-4594-9e4a-27e49cf8b9d4/search"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BASEPLATE_API_KEY}"
    }

    data = {
        "query": value,
        "top_k": 20,
        "filter": {"zip": {"$in": zip_codes}, "type":care_type},
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

def generate_zip_range(user_zip, range_size=5):
    user_zip_int = int(user_zip)
    return [str(user_zip_int - i) for i in range(range_size, 0, -1)] + [str(user_zip_int + i) for i in range(range_size + 1)]

def get_truncated_results(results, max_length=100):
    truncated_results = []
    for result in results:
        truncated_text = result['data']['text'][:max_length] + '...' if len(result['data']['text']) > max_length else result['data']['text']
        truncated_result = {
            "truncated_text": truncated_text,
            "title": result['data']['title'],
            "site_url": result['metadata']['site_url'],
            "desc": result['data']['desc']
        }
        truncated_results.append(truncated_result)
    return truncated_results

def get_truncated_provider_results(results, max_length=100):
    truncated_results = []
    for result in results:
        truncated_text = result['data']['text'][:max_length] + '...' if len(result['data']['text']) > max_length else result['data']['text']
        truncated_result = {
            "truncated_text": truncated_text,
            "name": result['data']['name'],
            "rating": result['data']['rating'],
            "site": result['data']['site'],
            "loc": result['data']['loc']
        }
        truncated_results.append(truncated_result)
    return truncated_results

def extract_care_data(survey_data):
    def dict_to_string(data):
        formatted_string = ""
        for key, value in data.items():
            formatted_string += key + ": " + str(value) + "\n"
        return formatted_string

    if isinstance(survey_data, dict):
        survey_data = dict_to_string(survey_data)

    print("Survey data:")
    print(survey_data)

    care_type = ""
    user_zip = ""
    first_name = ""

    name_search = re.search(r"What's your first and last name\? (.*?)  ", survey_data)
    if name_search:
        full_name = name_search.group(1)
        first_name = full_name.split(' ')[0]

    care_preferences_search = re.search(r"What are your/your loved one’s care preferences\? (.*?)  ", survey_data)
    if care_preferences_search:
        care_preferences = care_preferences_search.group(1)
        if "Residential Care" in care_preferences:
            care_type = "Memory Care"
        elif "Adult Day Care" in care_preferences:
            care_type = "Adult Care"
        else:
            care_type = "Home Care"

    user_zip_search = re.search(r"Finally, what is your zip code\? (\d+)", survey_data)
    if user_zip_search:
        user_zip = user_zip_search.group(1)

    return first_name, care_type, user_zip

    def handler(event: dict, context: dict) -> Tuple[str, int, dict]:

        if event['httpMethod'] != 'POST':
            return json.dumps({"message": "Invalid method"}), HTTPStatus.METHOD_NOT_ALLOWED, {'Content-Type': 'application/json'}

        print(f"Received event: {event}")

        try:
            typeform_data = json.loads(event['body'])
            first_name, care_type, user_zip = extract_care_data(typeform_data)

            print("Care Type:", care_type)
            print("User Zip:", user_zip)
            print("First Name:", first_name)

            template = """Subject: Your Mosaic Care Plan

            Dear {first_name},

            I wanted to personally reach out and thank you for entrusting Mosaic Care Solutions to help you find solutions for your loved one's care needs. We understand that navigating care services for older adults can be overwhelming, and we're here to help ease your burden.

            Once you have the right care in place, you will find the journey of caregiving to be rewarding and fulfilling. Our job is to help you get there as quickly and easily as possible. Our curated set of options will enable you to choose the right care solution for your loved one’s needs and preferences.

            Please find below your curated set of care options based on the questionnaire you completed. We provide tailored resources based on what we think will be most useful for you. We recommend that you also leverage the knowledge library, community support group and virtual assistant included in your membership. Together, they provide the mosaic of support and resources to help you and your loved one.

            Thank you for trusting Mosaic Care Solutions.

            Sincerely,
            Mosaic Care Team
            """

            prompt = PromptTemplate(template=template, input_variables=["first_name"])
            formatted_prompt = prompt.format(first_name=first_name)
            email_opening = formatted_prompt
            print(email_opening)

            provider_query = openaichat.generate_care_provider_query(survey_data)
            research_query = openaichat.generate_research_query(survey_data)

            research_vector_query_result = query_vector_database(research_query)
            truncated_research_vector_query_result = get_truncated_results(research_vector_query_result['results'], max_length=500)
            print(truncated_research_vector_query_result)

            reading_list = openaichat.generate_reading_list(truncated_research_vector_query_result, research_query)
            print(reading_list)

            zip_codes = generate_zip_range(user_zip)
            provider_vector_query_result = query_provider_database(provider_query, care_type, zip_codes)
            truncated_provider_vector_query_result = get_truncated_provider_results(provider_vector_query_result['results'], max_length=5)
            print(truncated_provider_vector_query_result)

            providers_list = openaichat.generate_providers_list(truncated_provider_vector_query_result, provider_query)
            print(providers_list)

            email_body = email_opening + "\n\nHere are some care providers based on your preferences:\n\n" + providers_list + "\n\nHere is a reading list we think you'll find useful:\n\n" + reading_list

            return json.dumps({"message": "Plan generated successfully", "user_plan": email_body}), HTTPStatus.OK, {'Content-Type': 'application/json'}

        except Exception as e:
            print(f"An error occurred: {e}")
            return json.dumps({"message": "An error occurred"}), HTTPStatus.INTERNAL_SERVER_ERROR, {'Content-Type': 'application/json'}
