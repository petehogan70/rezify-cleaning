import json
import os
from openai import OpenAI
import time
import PyPDF2
from sentry_sdk import capture_exception, capture_message

from backend.session_management import get_param_from_db, save_param_to_db
from backend.login import get_user_from_email
from backend.monitoring import add_search_data

WEBSITE_ENDPOINT = os.getenv("WEBSITE_ENDPOINT", "https://rezify.ai")  # Default to rezify if not set


# Define the Azure OpenAI credentials
ENDPOINT = os.getenv('OPENAI_API_ENDPOINT')
MAIN_SEARCH_API_KEY = os.getenv('MAIN_SEARCH_API_KEY')
MESSAGE_GENERATION_API_KEY = os.getenv('MESSAGE_GENERATION_API_KEY')
MODEL_NAME = "gpt-4o-mini"
ADD_TITLE_API_KEY = os.getenv('ADD_TITLE_API_KEY')
REFRESH_JOBS_API_KEY = os.getenv('REFRESH_JOBS_API_KEY')
ELASTICSEARCH_EMBEDDINGS_API_KEY = os.getenv('ELASTICSEARCH_EMBEDDINGS_API_KEY')
API_VERSION = "2024-02-01"
TITLE_MODEL_NAME = "text-embedding-3-small"  # Using small text embeddings for job titles
DESCRIPTION_MODEL_NAME = "text-embedding-3-small"  # Using small text embeddings for job descriptions

main_search_client = OpenAI(
    api_key=MAIN_SEARCH_API_KEY,
    organization=os.getenv('OPENAI_ORGANIZATION'),
)

message_generation_client = OpenAI(
    api_key=MESSAGE_GENERATION_API_KEY,
    organization=os.getenv('OPENAI_ORGANIZATION'),
)

# Create the OPENAI client for use
add_title_client = OpenAI(
    api_key=ADD_TITLE_API_KEY,
    organization=os.getenv('OPENAI_ORGANIZATION'),
)

refresh_jobs_client = OpenAI(
    api_key=REFRESH_JOBS_API_KEY,
    organization=os.getenv('OPENAI_ORGANIZATION'),
)

elasticsearch_embeddings_client = OpenAI(
    api_key=ELASTICSEARCH_EMBEDDINGS_API_KEY,
    organization=os.getenv('OPENAI_ORGANIZATION'),
)


def get_single_title_embedding(title, search_type):
    """
    Fetches the embedding for the title entered using the Azure OpenAI API.

    :return: the 256 dimension embeddings or None
    """
    try:
        if search_type == 'add_title':
            response = add_title_client.embeddings.create(
                input=title,
                model=TITLE_MODEL_NAME,
                dimensions=256  # 256 dimensions for titles
            )
        elif search_type == 'refresh_jobs':
            response = refresh_jobs_client.embeddings.create(
                input=title,
                model=TITLE_MODEL_NAME,
                dimensions=256  # 256 dimensions for titles
            )
        else:
            response = main_search_client.embeddings.create(
                input=title,
                model=TITLE_MODEL_NAME,
                dimensions=256  # 256 dimensions for titles
            )

        # Return the 256 dimension embeddings
        return response.data[0].embedding
    except Exception as e:
        capture_exception(e)
        return None



def get_single_description_embedding(description, search_type):
    """
        Fetches the embedding for the description entered using the Azure OpenAI API.

        :return: the 256 dimension embeddings or None
        """
    try:
        if search_type == 'add_title':
            response = add_title_client.embeddings.create(
                input=description,
                model=DESCRIPTION_MODEL_NAME,
                dimensions=256  # 256 dimension embedding
            )
        elif search_type == 'refresh_jobs':
            response = refresh_jobs_client.embeddings.create(
                input=description,
                model=DESCRIPTION_MODEL_NAME,
                dimensions=256  # 256 dimension embedding
            )
        else:
            response = main_search_client.embeddings.create(
                input=description,
                model=DESCRIPTION_MODEL_NAME,
                dimensions=256  # 256 dimension embedding
            )
        return response.data[0].embedding
    except Exception as e:
        capture_exception(e)
        return None


def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a given PDF file.
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text()

        return text
        # return "PDF parsing temporarily disabled for testing"
    except Exception as e:
        capture_exception(e)
        return ""



def get_parsed_from_resume(resume_path):
    """
    Parsing the resume entered using OpenAI API. It extracts the text from the PDF file and sends it to the OpenAI API
    for parsing. Getting internship recommendations, first name, last name, email, and skills from the resume.
    :param resume_path: the resume entered, a path to a pdf file
    :return:
    """
    try:
        start_time = time.time()

        # Step 1: Get the text from the PDF resume entered
        resume_text = extract_text_from_pdf(resume_path)

        # Step 2: Enhanced prompt to extract more detailed information
        prompt = '''
            You are an AI bot designed to act as a professional for parsing resumes. You are given with resume and your job is to extract comprehensive information for personalized networking messages.

            Extract the following information:
            1. 'internships': 4 internship titles that the person with the resume should be looking for to get experience for their future career path
            2. 'first name': the first name of the person with the resume
            3. 'last name': the last name of the person with the resume
            4. 'email': the email of the person with the resume
            5. 'skills': the skills (both technical and soft skills combined) of the person with the resume
            6. 'reported_college': the college or university that the person with resume currently attends

            CRITICAL: You must respond with ONLY valid JSON format. No explanations, no additional text, just the JSON object.

            Example format:
            {
                "internships": ["Software Engineering Intern", "Data Science Intern", "Product Management Intern", "Research Intern"],
                "first name": "John",
                "last name": "Doe",
                "email": "john.doe@email.com",
                "skills": ["Python", "JavaScript", "Machine Learning", "Communication", "Leadership"],
                "reported_college": "Purdue University"
            }
            '''

        MESSAGES = [
            {"role": "system", "content": prompt},
            {"role": "user",
             "content": resume_text}
        ]

        # Step 3: If your API allows file uploads as part of the request payload
        response = main_search_client.chat.completions.create(
            model=MODEL_NAME,
            messages=MESSAGES,
        )

        # Step 4: Process the API's response
        if response.choices:
            user_request = response.choices[0].message.content  # Get the content of the response
        else:
            user_request = 'Error'
            capture_exception(Exception("ERROR: OpenAI response fail"))

        # Step 5: Extract the JSON part from the response
        # Try to find JSON content more robustly
        try:
            # First try to find JSON content between curly braces
            start_idx = user_request.find('{')
            end_idx = user_request.rfind('}')

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = user_request[start_idx:end_idx + 1]
                result_dict = json.loads(json_content)
            else:
                # Fallback: try to find 'json' keyword
                if 'json' in user_request.lower():
                    json_start = user_request.lower().index('json')
                    # Find the first { after 'json'
                    brace_start = user_request.find('{', json_start)
                    if brace_start != -1:
                        brace_end = user_request.rfind('}')
                        if brace_end != -1:
                            json_content = user_request[brace_start:brace_end + 1]
                            result_dict = json.loads(json_content)
                        else:
                            result_dict = 'Error'
                    else:
                        result_dict = 'Error'
                else:
                    result_dict = 'Error'
        except Exception as json_error:
            capture_exception(json_error)
            # Return default values instead of raising
            result_dict = "Error"

        total_time = time.time() - start_time

        # Return the dictionary with the parsed information and the time taken to parse
        return result_dict, round(total_time, 4)

    except Exception as e:
        capture_exception(e)
        return "Error", 0

def get_experiences_from_resume(resume_path, session_id, resume_file):
    """
    Parsing the resume entered for experiences using OpenAI API. It extracts the text from the PDF file and sends it to the OpenAI API
    for parsing. Getting a list of experiences.
    :param resume_path: the resume entered, a path to a pdf file
    :param session_id: the session id of the user
    :param resume_file: the resume file name, used for error reporting
    :return:
    """
    try:
        start_time = time.time()

        # Step 1: Get the text from the PDF resume entered
        resume_text = extract_text_from_pdf(resume_path)

        # Step 2: Enhanced prompt to extract more detailed information
        prompt = '''
            You are an AI bot designed to act as a professional for parsing resumes. You are given with resume and your job is to extract comprehensive information for personalized networking messages.

            Extract the following information:
            - Experiences: JSON Array of experiences (work, project, research, extracurricular) with company / project names, roles, and brief descriptions

            CRITICAL: You must respond with ONLY valid JSON array format. No explanations, no additional text, just the Array object.

            Example format:
            [
                {"type": "Work", "company": "Tech Corp", "role": "Software Developer Intern", "description": "Built web applications using React and Node.js, improved database performance by 30%"},
                {"type": "Work", "company": "Data Solutions", "role": "Data Analyst", "description": "Analyzed customer data using Python and SQL, created dashboards in Tableau"},
                {"type": "Project", "project name, "description": "Led a team of 5 to develop a machine learning model for predicting student performance"},
                {"type": "Extracurricular", "organization": "Coding Club", "role": "President", "description": "Organized coding workshops and hackathons, increased club membership by 50%"}
            ]
            '''

        MESSAGES = [
            {"role": "system", "content": prompt},
            {"role": "user",
             "content": resume_text}
        ]

        # Step 3: If your API allows file uploads as part of the request payload
        response = main_search_client.chat.completions.create(
            model=MODEL_NAME,
            messages=MESSAGES,
        )

        # Step 4: Process the API's response
        if response.choices:
            user_request = response.choices[0].message.content  # Get the content of the response
            user_request = _safe_parse_json_array(user_request)
            exp_success = True
        else:
            capture_exception(Exception("ERROR: OpenAI response fail in get_experiences_from_resume"))
            user_request = 'Error'
            exp_success = False

        resume_info = get_param_from_db('resume_info', session_id)

        resume_dict = json.loads(resume_info) if isinstance(resume_info, str) else resume_info

        resume_dict['experiences'] = user_request

        save_param_to_db('resume_info', json.dumps(resume_dict), session_id)

        success, user = get_user_from_email(get_param_from_db('user_email', session_id))

        if success:
            filtered_resume = {
                k: v for k, v in resume_dict.items()
                if k in ["experiences", "relevant_coursework"]
            }
            # if you want it back as JSON string
            resume_json = filtered_resume

            resume_json = json.dumps(resume_json)
            user.update_user_param('resume_json', resume_json)

        total_time = round(time.time() - start_time, 4)

        if WEBSITE_ENDPOINT.lower() == "https://rezify.ai":
            add_search_data(total_time, 'parse_exp', resume_dict.get('email'), {})

        # Return the dictionary with the parsed information and the time taken to parse
        return exp_success, round(total_time, 4)

    except Exception as e:
        capture_exception(e)
        resume_info = get_param_from_db('resume_info', session_id)
        capture_message(f"Error in get_experiences_from_resume for resume {resume_info}: {e}", level="error")
        return False, 0


def _safe_parse_json_array(s: str):
    """
    Parse a JSON array from a model response that might include code fences or extra text.
    Returns a Python list or raises ValueError.
    """
    s = s.strip()

    # Strip code fences like ```json ... ```
    if s.startswith("```"):
        # remove first fence line
        s = s.split("\n", 1)[1] if "\n" in s else s
        # remove trailing ```
        if s.endswith("```"):
            s = s[:-3]

    # Trim to the first [...] block
    start = s.find('[')
    end = s.rfind(']')
    if start != -1 and end != -1 and end > start:
        s = s[start:end+1]

    data = json.loads(s)  # let this raise on invalid JSON
    if not isinstance(data, list):
        capture_exception(ValueError("Top-level JSON is not an array"))
    return data

def generate_talking_points(user, job, job_description):
    """
    Generates key talking points by analyzing resume and job description overlap.

    :param user: User object containing resume information and other info
    :param job: Job object from database
    :param job_description: HTML job description
    :return: List of talking point dictionaries
    """

    resume_info = user.resume_json
    try:
        # Create a comprehensive resume text from the resume_info
        exp_text = ""
        if resume_info.get('experiences'):
            exp_text = "\nExperiences:\n"
            for exp in resume_info.get('experiences', []):
                for label, value in exp.items():
                    exp_text += f"- {label.capitalize()}: {value.capitalize()}\n"

                exp_text += "\n"

        resume_text = f"""
        Name: {user.first_name} {user.last_name}
        Email: {user.email}
        College: {user.reported_college}

        Skills: {', '.join(user.skills)}

        Experience: {exp_text}

        IMPORTANT: Use specific experiences, projects, and achievements from above to create meaningful talking points that show real value and fit for the job.
        """

        job_text = f"""
        Job Title: {job.get('title', '')}
        Company: {job.get('company', '')}
        Location: {job.get('location', '')}

        Job Description:
        {job_description}
        """

        prompt = f"""
        You are an expert career coach analyzing a student's resume and a job posting to identify the strongest talking points for networking outreach.

        STUDENT'S RESUME:
        {resume_text}

        JOB POSTING:
        {job_text}

        Your task is to create 4-5 HYPER-PERSONALIZED talking points that show specific connections between this student's actual experiences and this exact job opportunity.

        CRITICAL REQUIREMENTS:
        1. Use ACTUAL project names, company names, technologies, and achievements from their resume and how they relate to the job
        2. Reference SPECIFIC requirements or keywords from the job description
        3. Make each point sound like the student wrote it about their own experience

        Return your response as a JSON array with this exact format:
        [
            {{
                "id": "point1",
                "text": "My [specific project/experience] using [exact technologies] directly addresses your need for [specific job requirement]"
            }},
            {{
                "id": "point2", 
                "text": "At [company/project], I [specific achievement with numbers] which aligns with your focus on [job requirement]"
            }}
        ]

        Return ONLY the JSON array, no additional text.
        """

        response = message_generation_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system",
                 "content": "You are a professional career coach specializing in student networking and outreach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        if response.choices:
            content = response.choices[0].message.content.strip()

            # Try to parse the JSON response
            try:
                talking_points = json.loads(content)
                return talking_points
            except json.JSONDecodeError as e:
                capture_exception(e)
                # Return fallback talking points
                return [
                    {"id": "skills",
                     "text": f"Your skills in {', '.join(resume_info.get('skills', [])[:2])} align with this role's requirements"},
                    {"id": "school",
                     "text": f"Your shared connection through {resume_info.get('reported_college', 'your university')} provides a great conversation starter"},
                    {"id": "interest",
                     "text": f"Your interest in {job.get('title', 'this role')} shows strong career alignment"},
                    {"id": "company",
                     "text": f"Your background makes you a strong fit for {job.get('company', 'this company')}'s mission"}
                ]

        else:
            capture_exception(Exception("ERROR: OpenAI response fail in generate_talking_points"))

        # Fallback if no response
        return [
            {"id": "skills", "text": "Your technical skills match the role requirements"},
            {"id": "school", "text": "Your university connection provides networking opportunities"},
            {"id": "interest", "text": "Your career interests align with this position"},
            {"id": "company", "text": "Your background fits the company culture"}
        ]

    except Exception as e:
        capture_exception(e)
        # Return basic fallback talking points
        return [
            {"id": "education", "text": "Your educational background aligns with the role requirements"},
            {"id": "skills", "text": "Your skill set matches what they're looking for"},
            {"id": "interest", "text": "Your career goals align with this opportunity"},
            {"id": "connection", "text": "Your shared school connection opens networking doors"}
        ]


def generate_personalized_message(user, job, job_description, selected_talking_points, message_goal,
                                  message_length='standard'):
    """
    Generates a personalized outreach message using the master prompt template.

    :param user: User object containing resume information
    :param job: Job object from database
    :param job_description: HTML job description
    :param selected_talking_points: List of selected talking point texts
    :param message_goal: The user's goal for the message
    :param message_length: Desired length of the message ('brief', 'standard', 'detailed')
    :return: Generated message string
    """
    try:
        # Define strict word count requirements based on message_length parameter
        length_requirements = {
            'brief': 'CRITICAL: Keep the message under 300 characters EXACTLY. Count every character carefully.',
            'standard': 'CRITICAL: Write the message between 80-120 words EXACTLY. This is a strict requirement.',
            'detailed': 'CRITICAL: Create a message between 120-180 words EXACTLY. Do not exceed this range.'
        }
        length_instruction = length_requirements.get(message_length, length_requirements['standard'])

        # Create the master prompt
        master_prompt = f"""
Role: You are "Rezify Co-Pilot," an expert career coach and communications strategist. Write a natural, conversational LinkedIn message that sounds like it was written by a real student, not a bot.

Context:

Student Information:
- Name: {user.first_name} {user.last_name}
- Email: {user.email}
- School: {user.reported_college}

Job Information:
- Title: {job.get('title', '')}
- Company: {job.get('company', '')}
- Location: {job.get('location', '')}
- Description: {job_description}

Selected Talking Points (use these to show fit):
{selected_talking_points}

Message Goal: {message_goal}

Task:
Write a personalized LinkedIn message that sounds natural and conversational. {length_instruction} Follow this structure:

1. PERSONAL GREETING: Start with "Hey [Name]!" and introduce yourself with your actual name and school
2. PURPOSE: Mention the specific job title and that you recently applied or are interested
3. CONNECTION/FIT: Use 1-2 of the selected talking points to show why you're a good fit, but make it conversational and SPECIFIC. Reference actual projects, work experiences, or achievements from their resume. For example:
   - Instead of "I have Python experience" → "I built a machine learning classifier using Python and scikit-learn for my capstone project"
   - Instead of "I have teamwork skills" → "I led a team of 4 developers during my internship at Tech Corp where we improved database performance by 30%"
4. LOCATION/PERSONAL TOUCH: If relevant, mention location or any personal connection
5. ASK: Based on the goal:
   - "Learn about the role": Ask for a brief chat to learn more
   - "Ask for a referral": Ask if they think you'd be a good fit and if they could refer you
   - "General networking": Ask to stay in touch and learn about opportunities

6. CLOSING: Thank them and sign with your actual name

CRITICAL REQUIREMENTS:
- Use the student's ACTUAL name ({user.first_name} {user.last_name})
- Use their ACTUAL school ({user.reported_college})
- Include their ACTUAL email ({user.email}) at the end
- Reference SPECIFIC projects, work experiences, or achievements from their resume data

FINAL WORD COUNT CHECK: Before returning your response, count the words in your message. It MUST be within the specified range: {length_requirements.get(message_length, '80-120 words')}. If it's outside this range, revise it to fit exactly.

Output: Return only the raw text of the message.
"""

        response = message_generation_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system",
                 "content": "You are Rezify Co-Pilot, an expert career coach specializing in personalized outreach messages for university students."},
                {"role": "user", "content": master_prompt}
            ],
            temperature=0.8,
            max_tokens=400
        )

        if response.choices:
            message = response.choices[0].message.content.strip()
            return message

        return f"""Hey there!

My name is {user.first_name} and I'm a student at {user.reported_college}. I recently came across the {job.get('title', '')} position at {job.get('company', '')} and I'm really interested in learning more about it.

Based on my experience, it seems like I could be a good fit for this role.

Would you be open to a brief chat about the role and your experience at {job.get('company', '')}? I'd really appreciate any insights you could share!

Thanks so much!

Best,
{user.first_name} {user.last_name}
{user.email}"""

    except Exception as e:
        capture_exception(e)
        # Return a basic fallback message
        return f"""Hey there!

        My name is {user.first_name} and I'm a student at {user.reported_college}. I recently came across the {job.get('title', '')} position at {job.get('company', '')} and I'm really interested in learning more about it.

        Based on my experience, it seems like I could be a good fit for this role.

        Would you be open to a brief chat about the role and your experience at {job.get('company', '')}? I'd really appreciate any insights you could share!

        Thanks so much!

        Best,
        {user.first_name} {user.last_name}
        {user.email}"""