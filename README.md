# 🎯 HireSense

> the resume screener that actually reads the room (and your resumes) 💅

No cap, hiring managers reading 200 resumes by hand is *not* it. HireSense throws your candidates' resumes at an AI, gets the real tea on who's actually qualified, and auto-emails everyone the verdict. It's giving efficient.

---

## ✨ what it do

- 📤 **Upload resumes** (drag & drop, we fancy) straight from the React frontend
- 🧠 **RAG-powered evaluation** — LlamaIndex chunks + embeds each resume into ChromaDB, then retrieves the most relevant sections before the LLM scores it against the actual job requirements, not just keyword matching
- 🔀 **Multi-provider LLM fallback** — tries Groq → OpenRouter → Gemini in that order, so a rate limit on one provider doesn't take the whole pitch down
- 🏷️ **Auto-sorts candidates** into Highly Suitable / Suitable / Not Suitable — no more manual triage
- 📧 **Sends the emails for you** — congrats, waitlist, or "it's not you it's your skillset" rejections, fully automated via SendGrid
- 🗂️ list / download / delete uploaded files whenever

## 🧱 the stack

**Backend:** FastAPI · MongoDB · ChromaDB · LlamaIndex · Groq / OpenRouter / Google Gemini (LLM) · Gemini embeddings · SendGrid HTTP API
**Frontend:** React 19 · TypeScript · Vite · Tailwind · MUI · Axios
**Deployed on:** Render (backend) + Vercel (frontend)

## 🚀 running this locally

### backend

```bash
pip install -r requirements.txt
```

Make sure MongoDB is running locally (`mongodb://localhost:27017/`), then drop a `.env` in the root (see `.env.example`):

```
GOOGLE_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=a_sendgrid_verified_sender_email
MONGO_URI=mongodb://localhost:27017/
FRONTEND_ORIGINS=http://localhost:5173
```

Only `GOOGLE_API_KEY` (for embeddings) is required to boot. For the evaluation LLM, at least one of `GROQ_API_KEY` / `OPENROUTER_API_KEY` is recommended — without either, it falls back to Gemini's free tier, which is capped low enough to run out mid-demo. `SENDGRID_API_KEY` + `SENDGRID_FROM_EMAIL` are only needed if you want candidate emails to actually send; the sender address must be verified in SendGrid under Single Sender Verification.

> ⚠️ **do NOT commit your `.env`.** It's already gitignored — keep it that way. If a secret ever leaks into git history, rotating it isn't optional, it's step one.

Then fire it up:

```bash
uvicorn main:app --reload
```

### frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`, talks to the backend on `http://localhost:8000`.

## 🔐 heads up

This is a project in progress — don't ship it to prod as-is without a proper look at auth, rate limiting, and dependency versions. We already patched the scary path-traversal stuff, but treat this like the MVP it is.

## 🤝 contributing

PRs welcome. Keep secrets out of commits, keep code readable, keep vibes immaculate. ✌️
