import os
import signal
import subprocess
import sys
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# إغلاق واجهات التوثيق بالكامل لحماية الروابط من المتصفح والمتطفلين
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# تخزين البوتات المشغلة: bot_id -> {"process": proc, "token": token, "owner": owner_id}
running_bots = {}

# الحد الأقصى للبوتات النشطة في نفس الوقت لحماية موارد السيرفر
MAX_CONCURRENT_BOTS = 40


class BotPayload(BaseModel):
    bot_token: str
    owner_id: str


class StopPayload(BaseModel):
    bot_token: str


def verify_telegram_token(token: str) -> dict:
    """
    التحقق من صحة التوكن مباشرة من خوادم تيليجرام الرسمية
    """
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if response.status_code == 200 and data.get("ok"):
            return {
                "valid": True,
                "bot_info": data.get("result", {})
            }
        return {"valid": False, "error": data.get("description", "توكن غير صالح")}
    except Exception:
        return {"valid": False, "error": "تعذر الاتصال بخوادم تيليجرام للتحقق من التوكن"}


@app.get("/")
def home():
    return {"status": "online", "message": "FarsLogic Bot Host is running safely"}


@app.post("/start_bot")
def start_bot(data: BotPayload):
    token = data.bot_token.strip()
    owner = str(data.owner_id).strip()

    # 1. فحص بنية التوكن والآيدي
    if ":" not in token or len(token) < 20:
        raise HTTPException(
            status_code=400,
            detail="صيغة التوكن غير صحيحة، تأكد من نسخه بشكل سليم من BotFather"
        )

    if not owner.isdigit() or int(owner) <= 0:
        raise HTTPException(
            status_code=400,
            detail="آيدي المالك غير صالح، يجب أن يتكون من أرقام فقط"
        )

    # 2. فحص هل التوكن حقيقي وموجود في تيليجرام؟
    check = verify_telegram_token(token)
    if not check["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"فشل التحقق: {check['error']}"
        )

    bot_info = check["bot_info"]
    bot_id = str(bot_info["id"])
    bot_username = bot_info.get("username", "Unknown")

    # 3. فحص سعة السيرفر لتفادي الضغط
    if len(running_bots) >= MAX_CONCURRENT_BOTS and bot_id not in running_bots:
        raise HTTPException(
            status_code=503,
            detail="السيرفر ممتلئ حالياً لتفادي الضغط، يرجى المحاولة بعد قليل"
        )

    # 4. إنهاء أي نسخة سابقة لنفس البوت إذا كانت تعمل أو معلقة
    if bot_id in running_bots:
        old_proc = running_bots[bot_id]["process"]
        try:
            old_proc.terminate()
            old_proc.wait(timeout=2)
        except Exception:
            try:
                old_proc.kill()
            except Exception:
                pass
        del running_bots[bot_id]

    # 5. تجهيز متغيرات البيئة وتشغيل البوت
    env_vars = os.environ.copy()
    env_vars["BOT_TOKEN"] = token
    env_vars["OWNER_ID"] = owner

    try:
        proc = subprocess.Popen(
            [sys.executable, "bot.py"],
            env=env_vars
        )
        running_bots[bot_id] = {
            "process": proc,
            "token": token,
            "owner": owner
        }
        return {
            "status": "success",
            "message": f"تم تشغيل البوت (@{bot_username}) بنجاح!",
            "bot_id": bot_id,
            "username": bot_username
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="حدث خطأ داخلي أثناء بدء العملية داخل الخادم"
        )


@app.post("/stop_bot")
def stop_bot(data: StopPayload):
    token = data.bot_token.strip()
    if ":" not in token:
        raise HTTPException(status_code=400, detail="توكن غير صالح")

    bot_id = token.split(":")[0]

    if bot_id in running_bots:
        # التحقق من أن التوكن مطابق لمنع أي شخص من إيقاف بوت غيره
        if running_bots[bot_id]["token"] != token:
            raise HTTPException(
                status_code=403,
                detail="غير مصرح لك بإيقاف هذا البوت"
            )

        proc = running_bots[bot_id]["process"]
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        del running_bots[bot_id]
        return {"status": "success", "message": "تم إيقاف البوت بنجاح!"}

    return {"status": "not_running", "message": "البوت غير مشغل حالياً أو متوقف مسبقاً."}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
