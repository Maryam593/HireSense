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
from llama_index.llms.openai_like import OpenAILike
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()
google_api = os.environ.get("GOOGLE_API_KEY")
groq_api = os.environ.get("GROQ_API_KEY")
openrouter_api = os.environ.get("OPENROUTER_API_KEY")
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
    elif openrouter_api:
        language_model = OpenAILike(
            model="openai/gpt-oss-20b:free",
            api_base="https://openrouter.ai/api/v1",
            api_key=openrouter_api,
            is_chat_model=True,
            context_window=128000,
        )
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
        if not email_matches:
            # Some PDF exports (e.g. certain design-tool templates) render text with a
            # space inserted between every character, breaking the regex above.
            # If the email sits alone on its own line (bounded by real newlines),
            # collapsing that line's spaces and requiring an exact full-line match
            # lets us safely allow digits in the local part (e.g. "kinza1291555").
            for line in document.text.split("\n"):
                if "@" not in line:
                    continue
                collapsed = re.sub(r"\s+", "", line)
                if re.fullmatch(r"[\w.-]+@[\w.-]+\.\w+", collapsed):
                    email_matches = [collapsed]
                    break
            if not email_matches:
                # No clean newline isolation - fall back to a stricter letters-only
                # heuristic to avoid swallowing adjacent phone-number digits.
                spaced_match = re.search(
                    r"([a-zA-Z]\s?){2,40}@\s?([\w.]\s?){1,40}\.\s?([a-zA-Z]\s?){2,4}",
                    document.text,
                )
                if spaced_match:
                    email_matches = [re.sub(r"\s+", "", spaced_match.group(0))]
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
                email_subject = "🎉 You're a Strong Match for the Software Engineer Role"
                email_body = f"""
Hey there,

Good news — we ran your resume against what we're actually looking for, and you're checking every
box for the Associate Software Engineer role. That's a genuinely strong fit.

We'd like to move you forward to the next step. Someone will follow up shortly with details, no
vague "we'll be in touch" energy here.

Nice resume. Talk soon.

- The Hiring Team (powered by HireSense)
"""
            elif len(matching_skills) > 0:
                suitability = "Suitable"
                email_subject = "Your Application: Here's Exactly Where You Stand"
                email_body = f"""
Hey there,

Thanks for applying for the Associate Software Engineer role. Instead of leaving you guessing, here's
the real breakdown of how your resume matched up:

✅ What's already working for you: {', '.join(matching_skills)}
📌 What would strengthen your profile: {', '.join(missing_skills)}

You're in the running, not a lock yet. Investing some time in the skills above would genuinely move
the needle, for this role or your next application anywhere.

We'll keep evaluating and follow up if it's a fit on our end.

Rooting for you,
The Hiring Team (powered by HireSense)
"""
            else:
                suitability = "Not Suitable"
                email_subject = "Your Application: Honest Feedback Inside"
                email_body = f"""
Hey there,

Thanks for taking the time to apply for the Associate Software Engineer role. Being upfront: based on
your resume as it stands, we're not moving forward for this specific role.

Here's what most companies won't bother telling you: the skills that would make the biggest difference
for a role like this are: {', '.join(missing_skills)}.

That's not a verdict on you, it's a gap map. Close a few of these and your next application hits
different, here or anywhere else.

Good luck out there,
The Hiring Team (powered by HireSense)
"""

            print(f"Suitability: {suitability}, email_body: {email_body}")
            if email_sender:
                email_sender.send(candidate_email, email_subject, email_body)
            else:
                print("Email not sent: SENDGRID_API_KEY/SENDGRID_FROM_EMAIL not configured.")

        else:
            print("Could not find a valid email address in the resume.")
    


