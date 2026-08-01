import os
import time
import chromadb
import re
import requests
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, PromptTemplate
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.llms.groq import Groq
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()
google_api = os.environ.get("GOOGLE_API_KEY")
groq_api = os.environ.get("GROQ_API_KEY")
job_skills = ["Python", "React", "JavaScript", "SQL", "Django", "AWS", "Git", "HTML", "CSS"]

def evaluate_resumes_and_send_emails():
    """
    Analyzes resumes from a folder, checks if they match a job description,
    and sends emails to candidates based on how well they fit.

    Args:
        resumes_folder (str): The path to the folder containing the resume files (e.g., "./resumes").
        your_email (str): Your email address to send emails from (e.g., "hiring_manager@gmail.com").
        your_app_password (str): A special password you generate for apps to access your email
            (check your email provider's settings).
        job_skills (list, optional): A list of important skills for the job.
            Defaults to a common set of web development skills.
        google_api (str, optional): Your Google API key. If you don't provide it here,
            the code will try to find it in your computer's settings.
    """

    # --- Step 1: Read the resumes ---
    documents = SimpleDirectoryReader("./data").load_data()
    print(f"{len(documents)} resume(s) found in ''.")
    embedding_model = GeminiEmbedding(model_name="models/gemini-embedding-001", api_key=google_api)

    # This is the main AI model that reads and understands the resumes
    if groq_api:
        language_model = Groq(model="llama-3.3-70b-versatile", api_key=groq_api)
    else:
        language_model = Gemini(model_name="models/gemini-flash-latest", api_key=google_api)
    client = chromadb.Client()
    resume_database = client.get_or_create_collection("resume_analysis")
    vector_store = ChromaVectorStore(chroma_collection=resume_database)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context,embed_model=embedding_model)

    # --- Step 4: Define how the AI should evaluate each resume ---
    evaluation_prompt = PromptTemplate(
        """
        You are a helpful AI assistant evaluating resumes for an "Associate Software Engineer" role.
        Here are the key requirements for the role:
        1. Strong knowledge of MERN Stack (MongoDB, Express.js, React, Node.js).
        2. Experience with designing and using RESTful APIs.
        3. Understanding of middleware for handling requests.
        4. Familiarity with token-based authentication (like JWT).
        5. Ability to create responsive web designs.
        6. Strong problem-solving skills.
        7. Ability to work independently and suggest new ideas.
        8. A creative mindset for improving user experience.
        9. Awareness of current tech trends.
        10. Proficient in using Git for version control.
        11. Experience with writing unit tests (like Jest or Mocha).
        12. Understanding of database design and optimization (like MongoDB).
        13. Familiarity with deploying web applications (like AWS or Heroku).
        14. Basic knowledge of CI/CD pipelines.
        15. Good communication and teamwork skills.
        16. Ability to adapt to changes and handle challenges.

        Based on the details in the resume below, please provide:
        - A rating of the candidate's suitability for this role (e.g., "Highly Suitable", "Suitable", "Not Suitable").
        - Key strengths that match the requirements.
        - Areas where the candidate could improve for this role.

        Resume: {context_str}
        Evaluation Question: How well does this resume match the Associate Software Engineer role requirements?
        Evaluation Answer:
        """
    )
    query_engine = index.as_query_engine(llm=language_model, prompt_template=evaluation_prompt, similarity_top_k=3)

    # --- Step 6: Class to handle sending emails ---
    # Uses the SendGrid HTTP API instead of raw SMTP, since Render blocks
    # outbound SMTP connections on its web services.
    class EmailSender:
        def __init__(self, sender_email, api_key):
            self.sender_email = sender_email
            self.api_key = api_key

        def send(self, recipient, subject, body):
            try:
                response = requests.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "personalizations": [{"to": [{"email": recipient}]}],
                        "from": {"email": self.sender_email},
                        "subject": subject,
                        "content": [{"type": "text/plain", "value": body}],
                    },
                    timeout=15,
                )
                response.raise_for_status()
                print(f"Email sent to {recipient}")
            except Exception as e:
                print(f"Error sending email to {recipient}: {e}")

    sendgrid_api_key = os.environ.get("SENDGRID_API_KEY")
    # Must be an email verified in SendGrid under Settings -> Sender Authentication -> Single Sender Verification.
    sender_email = os.environ.get("SENDGRID_FROM_EMAIL")
    email_sender = EmailSender(sender_email, sendgrid_api_key) if sendgrid_api_key and sender_email else None

    # --- Step 7: Go through each resume, evaluate it, and send an email ---
    for document in documents:
        single_resume_index = VectorStoreIndex.from_documents([document],
                                                            embed_model=embedding_model)
        single_resume_query_engine = single_resume_index.as_query_engine(
            llm=language_model, prompt_template=evaluation_prompt, similarity_top_k=1)

        # Get the AI's evaluation of the resume
        evaluation_result = single_resume_query_engine.query("Evaluate this resume.")
        print(f"\n--- Evaluation for: {document.metadata.get('file_name')} ---")
        print(f"AI Evaluation: {evaluation_result}")

        # Try to find the candidate's email address in the resume text
        email_matches = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", document.text)
        candidate_email = email_matches[0] if email_matches else None

        if candidate_email:
            print(f"Found email: {candidate_email}")

            # Try to extract skills mentioned in the resume
            skills_query = "List all the technical skills mentioned in this resume."
            skills_result = single_resume_query_engine.query(skills_query)
            found_skills = re.findall(r"\b(" + "|".join(job_skills) + r")\b",
                                     str(skills_result), re.IGNORECASE)
            found_skills = list(set(found_skills)) 

            matching_skills = [
                skill for skill in found_skills if skill.lower() in [js.lower() for js in job_skills]]
            missing_skills = [
                skill for skill in job_skills if skill.lower() not in [fs.lower() for fs in found_skills]]

            if len(matching_skills) == len(job_skills):
                suitability = "Highly Suitable"
                email_subject = "Congratulations! You're a Great Fit for Our Software Engineer Role"
                email_body = f"""
Dear Candidate,

We are very impressed with your resume and believe your skills and experience align well with the
requirements for our Associate Software Engineer role. We would like to invite you for the next step
in our hiring process.

We will be in touch soon with more details.

Best regards,
The Hiring Team
"""
            elif len(matching_skills) > 0:
                suitability = "Suitable"
                email_subject = "Your Application for Software Engineer - Waiting List"
                email_body = f"""
Dear Candidate,

Thank you for your interest in the Associate Software Engineer role. Your resume shows some promising
skills, including: {', '.join(matching_skills)}.

We are currently reviewing applications and will be in touch if your profile is selected for the next stage.

For your reference, some of the key skills we are looking for include: {', '.join(missing_skills)}.
You may want to highlight any experience you have in these areas in future applications.

Best regards,
The Hiring Team
"""
            else:
                suitability = "Not Suitable"
                email_subject = "Update on Your Application for Software Engineer"
                email_body = f"""
Dear Candidate,

Thank you for your application for the Associate Software Engineer role. After careful review, we have
decided not to move forward with your application at this time.

For future applications, we recommend focusing on developing skills in areas such as:
{', '.join(missing_skills)}.

We wish you the best in your job search.

Sincerely,
The Hiring Team
"""

            print(f"Suitability: {suitability}, email_body: {email_body}")
            if email_sender:
                email_sender.send(candidate_email, email_subject, email_body)
            else:
                print("Email not sent: SENDGRID_API_KEY/SENDGRID_FROM_EMAIL not configured.")

        else:
            print("Could not find a valid email address in the resume.")
    


