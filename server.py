import os
import signal
import subprocess
import sys
import time
import hmac
import hashlib
import requests
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

SECRET_SALT = "fars_secure_signature_salt_9988"

running_bots = {}
# ذاكرة لحفظ أرقام الطلبات المستهلكة لمنع تكرارها نهائياً
used_nonces = {}
MAX_CONCURRENT_BOTS = 40


class BotPayload(BaseModel):
    bot_token: str
    owner_id: str


class StopPayload(BaseModel):
    bot_token: str


def cleanup_nonces():
    """تنظيف الرموز التي مر عليها أكثر من 30 ثانية لتوفير الذاكرة"""
    now = time.time()
    expired = [n for n, exp in used_nonces.items() if exp < now]
    for n in expired:
        del used_nonces[n]


def verify_security(token: str, action: str, timestamp_str: str, nonce: str, signature: str) -> bool:
    """
    التحقق من: الوقت (15 ثانية) + الرمز غير مستخدم + التوقيع المشفر المطابق للعملية
    """
    if not timestamp_str or not nonce or not signature:
        return False

    try:
        cleanup_nonces()
        req_time = int(timestamp_str)
        current_time = int(time.time())

        # 1. مهلة زمنية صارمة: 15 ثانية فقط
        if abs(current_time - req_time) > 15:
            return False

        # 2. فحص هل تم استخدام هذا الطلب من قبل؟
        if nonce in used_nonces:
            return False  # محاولة تكرار مرفوضة فوراً

        # 3. التأكد من صحة التوقيع المشفر
        raw_data = f"{token}:{action}:{nonce}:{req_time}:{SECRET_SALT}".encode("utf-8")
        expected_sig = hashlib.sha256(raw_data).hexdigest()
        
        if not hmac.compare_digest(expected_sig, signature):
            return False

        # تسجيل الرمز لمنع استخدامه مرة ثانية نهائياً
        used_nonces[nonce] = current_time + 30
        return True
    except Exception:
        return False


def verify_telegram_token(token: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if response.status_code == 200 and data.get("ok"):
            return {"valid": True, "bot_info": data.get("result", {})}
        return {"valid": False, "error": data.get("description", "توكن غير صالح")}
    except Exception:
        return {"valid": False, "error": "تعذر الاتصال بخوادم تيليجرام للتحقق من التوكن"}


@app.get("/")
def home():
    return {"status": "online"}


@app.post("/start_bot")
def start_bot(
    data: BotPayload,
    x_timestamp: str = Header(None),
    x_nonce: str = Header(None),
    x_signature: str = Header(None)
):
    token = data.bot_token.strip()
    owner = str(data.owner_id).strip()

    # التحقق من الأمان بنوع العملية 'start'
    if not verify_security(token, "start", x_timestamp, x_nonce, x_signature):
        raise HTTPException(status_code=403, detail="طلب غير صالح أو مستخدم مسبقاً أو منتهي الصلاحية")

    if ":" not in token or len(token) < 20:
        raise HTTPException(status_code=400, detail="صيغة التوكن غير صحيحة")

    if not owner.isdigit() or int(owner) <= 0:
        raise HTTPException(status_code=400, detail="آيدي المالك غير صالح")

    check = verify_telegram_token(token)
    if not check["valid"]:
        raise HTTPException(status_code=400, detail=f"فشل التحقق: {check['error']}")

    bot_info = check["bot_info"]
    bot_id = str(bot_info["id"])
    bot_username = bot_info.get("username", "Unknown")

    if len(running_bots) >= MAX_CONCURRENT_BOTS and bot_id not in running_bots:
        raise HTTPException(status_code=503, detail="السيرفر ممتلئ حالياً، يرجى المحاولة لاحقاً")

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

    env_vars = os.environ.copy()
    env_vars["BOT_TOKEN"] = token
    env_vars["OWNER_ID"] = owner

    try:
        proc = subprocess.Popen([sys.executable, "bot.py"], env=env_vars)
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
        raise HTTPException(status_code=500, detail="حدث خطأ داخلي أثناء التشغيل")


@app.post("/stop_bot")
def stop_bot(
    data: StopPayload,
    x_timestamp: str = Header(None),
    x_nonce: str = Header(None),
    x_signature: str = Header(None)
):
    token = data.bot_token.strip()

    # التحقق بنوع العملية 'stop'
    if not verify_security(token, "stop", x_timestamp, x_nonce, x_signature):
        raise HTTPException(status_code=403, detail="طلب غير صالح أو مستخدم مسبقاً أو منتهي الصلاحية")

    bot_id = token.split(":")[0]

    if bot_id in running_bots:
        if running_bots[bot_id]["token"] != token:
            raise HTTPException(status_code=403, detail="غير مصرح لك بإيقاف هذا البوت")

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

    return {"status": "not_running", "message": "البوت غير مشغل حالياً."}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
