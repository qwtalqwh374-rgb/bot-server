import os
import signal
import subprocess
import sys
from fastapi import FastAPI, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI()
running_bots = {}


class BotPayload(BaseModel):
    bot_token: str
    owner_id: str


@app.get("/")
def home():
    return {"status": "online", "message": "Bot Maker Server is running!"}


@app.post("/start_bot")
def start_bot(data: BotPayload):
    token = data.bot_token.strip()
    owner = str(data.owner_id).strip()
    bot_id = token.split(":")[0]

    # فحص إذا كان البوت شغال بالفعل
    if bot_id in running_bots:
        proc = running_bots[bot_id]
        if proc.poll() is None:
            return {"status": "already_running", "message": "البوت يعمل بالفعل!"}

    env_vars = os.environ.copy()
    env_vars["BOT_TOKEN"] = token
    env_vars["OWNER_ID"] = owner

    try:
        # استخدام sys.executable لضمان استخدام نفس بايثون والبيئة الافتراضية
        # تم إزالة DEVNULL لتظهر رسائل بايثون وتيليجرام في سجلات Railway مباشرة
        proc = subprocess.Popen(
            [sys.executable, "bot.py"],
            env=env_vars
        )
        running_bots[bot_id] = proc
        return {
            "status": "success",
            "message": f"تم تشغيل البوت ({bot_id}) بنجاح!",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/stop_bot")
def stop_bot(bot_id: str = Query(...)):
    bot_id = bot_id.strip()
    if bot_id in running_bots:
        proc = running_bots[bot_id]
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
            del running_bots[bot_id]
            return {"status": "success", "message": "تم إيقاف البوت بنجاح!"}

    return {"status": "not_running", "message": "البوت متوقف بالفعل."}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
