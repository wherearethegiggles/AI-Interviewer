import asyncio
import os
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
from typing import Annotated
from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, tokenize, tts
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import deepgram, openai, silero
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import init_chat_model
from langchain.chains.summarize import load_summarize_chain

# Load environment variables
load_dotenv()

# Constants
RESUME_PATH = "/Users/mario/Downloads/AI Interviewer - Growhut/Vignesh-Prasath_Resume.pdf"
CSV_FILENAME = "interview_scores.csv"
HEADER = ["Timestamp", "Candidate Name", "Final Rating", "Remarks"]
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Load and summarize the resume
def load_and_summarize_resume(file_path: str):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    
    llm = init_chat_model("command-r", model_provider="cohere")
    summarize_chain = load_summarize_chain(llm, chain_type="map_reduce")
    summary = summarize_chain.invoke(texts)
    
    return summary.get("output_text", "Summary not available") if isinstance(summary, dict) else summary

# Extract candidate's name from summary
def extract_candidate_name(resume_summary: str):
    return resume_summary.split("\n")[0] if resume_summary else "Unknown Candidate"

resume_summary = load_and_summarize_resume(RESUME_PATH)
candidate_name = extract_candidate_name(resume_summary)

def write_to_csv(data: list):
    file_exists = os.path.isfile(CSV_FILENAME)
    with open(CSV_FILENAME, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)  # Write header only if file does not exist
        writer.writerow(data)

# Initialize GPT model
gpt = openai.LLM(model="gpt-4o")

# Interview Entry Point
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print(f"Room name: {ctx.room.name}")

    # Setup chat context
    chat_context = ChatContext(messages=[
        ChatMessage(
            role="system",
            content=(
                "You are a real human-like interviewer for an important role. Keep responses short. "
                "Ask 5 original questions excluding follow-up questions based on the answers. "
                "If the candidate answers vaguely 3 times, end the session. "
                "If they want to exit, confirm and disconnect. "
                "Once the interview is concluded, do not answer anything, just repeat that the interview is concluded. "
                "Politely call out unclear, incorrect, or nonsensical answers. "
                f"Resume: {resume_summary}"
            ),
        )
    ])
    
    # Setup Text-to-Speech adapter
    openai_tts = tts.StreamAdapter(
        tts=openai.TTS(voice="alloy"),
        sentence_tokenizer=tokenize.basic.SentenceTokenizer(),
    )
    
    interview_log = []
    bad_response_count = 0
    question_count = 0

    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=gpt,
        tts=openai_tts,
        chat_ctx=chat_context,
    )

    room = ctx.room

    def assess_response(response: str):
        nonlocal bad_response_count
        if "I don't know" in response or "umm" in response or len(response.split()) < 5:
            bad_response_count += 1
        else:
            bad_response_count = 0

    async def _answer(text: str):
        nonlocal question_count
        chat_context.messages.append(ChatMessage(role="user", content=text))
        interview_log.append({"role": "user", "message": text})
        
        stream = gpt.chat(chat_ctx=chat_context)
        response = await stream.text()
        interview_log.append({"role": "assistant", "message": response})
        
        assess_response(response)
        question_count += 1

        if text.lower() in ["end interview", "i want to leave"]:
            await assistant.say("Are you sure? Say 'yes' to confirm.", allow_interruptions=True)
            write_to_csv([TIMESTAMP, candidate_name, "N/A", "Candidate exited voluntarily."])
            await ctx.shutdown(reason="Session ended")
            return

        if bad_response_count >= 3:
            await assistant.say("We will get back to you. Interview ended.", allow_interruptions=True)
            write_to_csv([TIMESTAMP, candidate_name, "Fail", "Candidate struggled with responses."])
            await ctx.shutdown(reason="Session ended")
            return
        
        if question_count == 5:
            await assistant.say("That concludes the interview. We will evaluate your performance.", allow_interruptions=True)
            evaluation_result = await gpt.chat(chat_ctx=ChatContext(messages=[
                ChatMessage(role="system", content="Rate the candidate 1-10 and provide 2 lines of feedback."),
                ChatMessage(role="user", content=json.dumps(interview_log))
            ])).text()
            
            try:
                lines = evaluation_result.strip().split("\n")
                rating = lines[0].strip() if lines else "N/A"
                remarks = " ".join(lines[1:]).strip() if len(lines) > 1 else "No remarks provided."
            except Exception as e:
                rating, remarks = "N/A", f"Error extracting rating: {str(e)}"
            
            print(f"Timestamp: {TIMESTAMP}, Candidate Name: {candidate_name}, Final Rating: {rating}, Remarks: {remarks}")
            write_to_csv([TIMESTAMP, candidate_name, rating, remarks])
            await ctx.shutdown(reason="Session ended")
            return
        
        await assistant.say(response, allow_interruptions=True)
    
    @room.on("data_received")
    def on_message_received(packet: rtc.DataPacket):
        if packet.value:
            asyncio.create_task(_answer(packet.value))
    
    assistant.start(ctx.room)
    
    await asyncio.sleep(1)
    await assistant.say("Hello! Welcome to the interview. Let's start with an introduction. Can you tell me a bit about yourself?", allow_interruptions=True)
    
    await asyncio.sleep(60)
    await ctx.shutdown(reason="Session ended")

# Run the application
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, initialize_process_timeout=120))
