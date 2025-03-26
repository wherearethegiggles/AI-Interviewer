# AI Interviewer

First, create a virtual environment, update pip, and install the required packages:

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -U pip
$ pip install -r requirements.txt
```

You need to set up the following environment variables:

```
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
DEEPGRAM_API_KEY=...
OPENAI_API_KEY=...
COHERE_API_KEY=...
```
NOTE: Provide file_path for the resume.pdf on app.py code before you run. 

Then, run the app:

```
$ python3 app.py download-files
$ export SSL_CERT_FILE=$(python -m certifi) python3 app.py start
```

Finally, you can load the [hosted playground](https://agents-playground.livekit.io/) and connect it.



# Usage Guide

Admin Side (Interviewer Setup):

``` 

    Start the application using the command above.

    Upload a candidate’s resume (PDF format).

    The AI will summarize the resume and extract key points.

    The system generates interview questions based on the resume.

    The admin can monitor and assess the candidate’s responses.

    At the end, the AI provides a final rating and feedback.

```

Candidate Side (Interview Process):

    The candidate joins the interview session.

    The AI starts by asking an introduction question.

    The candidate answers verbally, and the AI:

    Processes responses using voice recognition.

    Evaluates responses based on clarity and accuracy.

    Asks follow-up questions dynamically.

    If the candidate gives three vague responses, the interview ends early.

    After five questions, the AI provides an overall rating and remarks.


# Notes & Known Issues

    Ensure that LiveKit, OpenAI, and Deepgram API keys are correctly configured.

    Resume must be in PDF format for proper summarization.

    Voice detection may sometimes misinterpret speech due to background noise.

    The AI does not currently support multilingual interviews (English only).

    The SSH certificate has to be updated. export SSL_CERT_FILE=$(python -m certifi)


# Future Improvements

    Add real-time video streaming capablities 

    Add multilingual support for non-English interviews.

    Implement real-time admin feedback controls to adjust interview flow.

    Improve speech recognition for better voice clarity and response analysis.

