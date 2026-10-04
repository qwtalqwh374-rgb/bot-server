import os
import subprocess
import sys

required_packages = ["pyrogram", "kvsqlite", "tgcrypto"]

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package]
            )
        except Exception:
            pass

# استقبال التوكن والآيدي من بيئة التشغيل الممررة من التطبيق والسيرفر
token = os.getenv("BOT_TOKEN", "توكن")
ownerID = int(os.getenv("OWNER_ID", "0"))

import asyncio
from datetime import date
from kvsqlite.sync import Client as DB
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from pyrogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

bot_id = token.split(":")[0]
db_file = f"botdb_{bot_id}.sqlite"
botdb = DB(db_file)

bot = Client(
    "bot" + bot_id,
    9398500,
    "ad2977d673006bed6e5007d953301e13",
    bot_token=token,
)

bot.start()

STARTKEY = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "( إذاعة للمستخدمين )", callback_data="broadcast"
            )
        ],
        [
            InlineKeyboardButton("( الاحصائيات )", callback_data="stats"),
            InlineKeyboardButton("( الأدمنية )", callback_data="adminstats"),
            InlineKeyboardButton("( المحظورين )", callback_data="bannedstats"),
        ],
        [InlineKeyboardButton("( جلب التخزين )", callback_data="Get")],
        [
            InlineKeyboardButton("( كشف مستخدم )", callback_data="whois"),
            InlineKeyboardButton("( حظر مستخدم )", callback_data="ban"),
        ],
        [
            InlineKeyboardButton("( إلغاء حظر )", callback_data="unban"),
        ],
        [
            InlineKeyboardButton("( رفع ادمن )", callback_data="addadmin"),
            InlineKeyboardButton("( تنزيل ادمن )", callback_data="remadmin"),
        ],
    ]
)
if not botdb.get("db" + token.split(":")[0]):
    data = {
        "users": [],
        "admins": [],
        "banned": [],
    }
    botdb.set("db" + token.split(":")[0], data)

if not ownerID in botdb.get("db" + token.split(":")[0])["admins"]:
    data = botdb.get("db" + token.split(":")[0])
    data["admins"].append(ownerID)
    botdb.set("db" + token.split(":")[0], data)


@bot.on_message(filters.command("start") & filters.private)
async def on_start(c, m):
    getDB = botdb.get("db" + token.split(":")[0])
    if m.from_user.id in getDB["banned"]:
        return await m.reply("🚫 تم حظرك من استخدام البوت", quote=True)
    if m.from_user.id == ownerID or m.from_user.id in getDB["admins"]:
        await m.reply(
            f"""
**• أهلاً بك ⌯ {m.from_user.mention} .
 — أليك لوحة الادمن ..
 — يمكنك من خلال اللوحة ان تتحكم بأعدادات البوت والرفع والتنزيل !
 — – — – — – — – — – — – —
 
- Join ...

**""",
            reply_markup=STARTKEY,
            quote=True,
        )
    if not m.from_user.id in getDB["users"]:
        data = getDB
        data["users"].append(m.from_user.id)
        botdb.set("db" + token.split(":")[0], data)
        for admin in data["admins"]:
            text = f"– New user stats the bot :"
            username = (
                "@" + m.from_user.username if m.from_user.username else "None"
            )
            text += f"\n\n𖡋 𝐔𝐒𝐄 ⌯  {username}"
            text += f"\n𖡋 𝐍𝐀𝐌𝐄 ⌯  {m.from_user.mention}"
            text += f"\n𖡋 𝐈𝐃 ⌯  `{m.from_user.id}`"
            text += f"\n𖡋 𝐃𝐀𝐓𝐄 ⌯  **{date.today()}**"
            try:
                await c.send_message(
                    admin,
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    m.from_user.first_name,
                                    user_id=m.from_user.id,
                                )
                            ]
                        ]
                    ),
                )
            except:
                pass
    data = {
        "name": m.from_user.first_name[:25],
        "username": m.from_user.username,
        "mention": m.from_user.mention(m.from_user.first_name[:25]),
        "id": m.from_user.id,
    }
    botdb.set(f"USER:{m.from_user.id}", data)


@bot.on_message(filters.private & ~filters.service)
async def on_messages(c, m):
    if botdb.get(f"broad:{m.from_user.id}") and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        text = "**— جاري إرسال الإذاعة إلى المستخدمين**\n"
        reply = await m.reply(text, quote=True)
        count = 0
        users = botdb.get("db" + token.split(":")[0])["users"]
        for user in users:
            try:
                await m.copy(user)
                count += 1
                await reply.edit(
                    text
                    + f"**— تم ارسال الإذاعة الى [ {count}/{len(users)} ] مستخدم**"
                )
            except FloodWait as x:
                await asyncio.sleep(x.value)
            except Exception:
                pass
        return True

    if (
        m.text
        and botdb.get(f"whois:{m.from_user.id}")
        and (
            m.from_user.id == ownerID
            or m.from_user.id
            in botdb.get("db" + token.split(":")[0])["admins"]
        )
    ):
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم بهذا الآيدي", quote=True)
        else:
            name = getUser["name"]
            id = getUser["id"]
            mention = getUser["mention"]
            username = (
                "@" + getUser["username"] if getUser["username"] else "None"
            )
            language = botdb.get(f"LANG:{id}")
            text = f"𖡋 𝐔𝐒𝐄 ⌯  {username}"
            text += f"\n𖡋 𝐍𝐀𝐌𝐄 ⌯  {name}"
            text += f"\n𖡋 𝐈𝐃 ⌯  `{id}`"
            text += f"\n𖡋 𝑳𝐀𝐍𝐆 ⌯  {language}"
            text += f"\n𖡋 𝐀𝐂𝐂 𝑳𝐈𝐍𝐊 ⌯  **{mention}**"
            return await m.reply(text, quote=True)

    if (
        m.text
        and botdb.get(f"ban:{m.from_user.id}")
        and (
            m.from_user.id == ownerID
            or m.from_user.id
            in botdb.get("db" + token.split(":")[0])["admins"]
        )
    ):
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم بهذا الآيدي", quote=True)
        else:
            if (
                getUser["id"]
                in botdb.get("db" + token.split(":")[0])["admins"]
            ):
                return await m.reply(
                    f"– لا يمكنك حظر ⌯ {getUser['mention']} ⌯ لأنه ادمن",
                    quote=True,
                )
            else:
                if (
                    getUser["id"]
                    in botdb.get("db" + token.split(":")[0])["banned"]
                ):
                    return await m.reply(
                        f"– لا يمكنك حظر ⌯ {getUser['mention']} ⌯ لأنه محظور مسبقاً",
                        quote=True,
                    )
                name = getUser["mention"]
                id = getUser["id"]
                username = (
                    "@" + getUser["username"]
                    if getUser["username"]
                    else "None"
                )
                language = botdb.get(f"LANG:{id}")
                text = f"- This user added to blacklist:\n\n"
                text += f"𖡋 𝐔𝐒𝐄 ⌯  {username}"
                text += f"\n𖡋 𝐍𝐀𝐌𝐄 ⌯  {name}"
                text += f"\n𖡋 𝑳𝐀𝐍𝐆 ⌯  {language}"
                text += f"\n𖡋 𝐈𝐃 ⌯  `{id}`"
                data = botdb.get("db" + token.split(":")[0])
                data["banned"].append(id)
                botdb.set("db" + token.split(":")[0], data)
                return await m.reply(text, quote=True)

    if (
        m.text
        and botdb.get(f"unban:{m.from_user.id}")
        and (
            m.from_user.id == ownerID
            or m.from_user.id
            in botdb.get("db" + token.split(":")[0])["admins"]
        )
    ):
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم بهذا الآيدي", quote=True)
        else:
            if (
                getUser["id"]
                in botdb.get("db" + token.split(":")[0])["admins"]
            ):
                return await m.reply(
                    f"– لا يمكنك الغاء حظر ⌯ {getUser['mention']} ⌯ لأنه ادمن",
                    quote=True,
                )
            else:
                if (
                    not getUser["id"]
                    in botdb.get("db" + token.split(":")[0])["banned"]
                ):
                    return await m.reply(
                        f"– لا يمكنك الغاء حظر ⌯ {getUser['mention']} ⌯ لأنه غير محظور مسبقاً",
                        quote=True,
                    )
                name = getUser["mention"]
                id = getUser["id"]
                username = (
                    "@" + getUser["username"]
                    if getUser["username"]
                    else "None"
                )
                language = botdb.get(f"LANG:{id}")
                text = f"- This user deleted from blacklist:\n\n"
                text += f"𖡋 𝐔𝐒𝐄 ⌯  {username}"
                text += f"\n𖡋 𝐍𝐀𝐌𝐄 ⌯  {name}"
                text += f"\n𖡋 𝑳𝐀𝐍𝐆 ⌯  {language}"
                text += f"\n𖡋 𝐈𝐃 ⌯  `{id}`"
                data = botdb.get("db" + token.split(":")[0])
                data["banned"].remove(id)
                botdb.set("db" + token.split(":")[0], data)
                return await m.reply(text, quote=True)

    if (
        m.text
        and botdb.get(f"add:{m.from_user.id}")
        and m.from_user.id == ownerID
    ):
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم بهذا الآيدي", quote=True)
        else:
            if (
                getUser["id"]
                in botdb.get("db" + token.split(":")[0])["admins"]
            ):
                return await m.reply(
                    f"– لا يمكنك رفع ⌯ {getUser['mention']} ⌯ لأنه ادمن مسبقاً",
                    quote=True,
                )
            if (
                getUser["id"]
                in botdb.get("db" + token.split(":")[0])["banned"]
            ):
                return await m.reply(
                    f"– لا يمكنك رفع ⌯ {getUser['mention']} ⌯ لأنه محظور",
                    quote=True,
                )
            else:
                name = getUser["mention"]
                id = getUser["id"]
                username = (
                    "@" + getUser["username"]
                    if getUser["username"]
                    else "None"
                )
                language = botdb.get(f"LANG:{id}")
                text = f"- This user added to admins list:\n\n"
                text += f"𖡋 𝐔𝐒𝐄 ⌯  {username}"
                text += f"\n𖡋 𝐍𝐀𝐌𝐄 ⌯  {name}"
                text += f"\n𖡋 𝑳𝐀𝐍𝐆 ⌯  {language}"
                text += f"\n𖡋 𝐈𝐃 ⌯  `{id}`"
                data = botdb.get("db" + token.split(":")[0])
                data["admins"].append(id)
                botdb.set("db" + token.split(":")[0], data)
                return await m.reply(text, quote=True)

    if (
        m.text
        and botdb.get(f"rem:{m.from_user.id}")
        and m.from_user.id == ownerID
    ):
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم بهذا الآيدي", quote=True)
        else:
            if (
                not getUser["id"]
                in botdb.get("db" + token.split(":")[0])["admins"]
            ):
                return await m.reply(
                    f"– لا يمكنك تنزيل ⌯ {getUser['mention']} ⌯ لأنه مو ادمن",
                    quote=True,
                )
            if getUser["id"] == ownerID:
                return await m.reply(
                    f"– لا يمكنك تنزيل ⌯ {getUser['mention']} ⌯ لأنه مالك البوت",
                    quote=True,
                )
            else:
                name = getUser["mention"]
                id = getUser["id"]
                username = (
                    "@" + getUser["username"]
                    if getUser["username"]
                    else "None"
                )
                language = botdb.get(f"LANG:{id}")
                text = f"- This user deleted from admins list:\n\n"
                text += f"𖡋 𝐔𝐒𝐄 ⌯  {username}"
                text += f"\n𖡋 𝐍𝐀𝐌𝐄 ⌯  {name}"
                text += f"\n𖡋 𝑳𝐀𝐍𝐆 ⌯  {language}"
                text += f"\n𖡋 𝐈𝐃 ⌯  `{id}`"
                data = botdb.get("db" + token.split(":")[0])
                data["admins"].remove(id)
                botdb.set("db" + token.split(":")[0], data)
                return await m.reply(text, quote=True)


@bot.on_callback_query()
async def on_Callback(c, m):
    if m.data == "Get" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        await m.answer(f"- انتضر  ❕", show_alert=True, cache_time=10)
        await bot.send_document(
            chat_id=m.from_user.id,
            document=open(db_file, "rb"),
            caption="- ملف تخزين البوت !",
        )
    if m.data == "broadcast" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        await m.edit_message_text(
            "• أرسل الإذاعة الآن ( صورة ، نص ، ملصق ، ملف ، صوت )\n• للإلغاء ارسل الغاء ",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]
            ),
        )
        botdb.set(f"broad:{m.from_user.id}", True)
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")

    if m.data == "whois" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        await m.edit_message_text(
            "• ارسل الآن ايدي المستخدم للكشف عنه\n• للإلغاء ارسل الغاء ",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]
            ),
        )
        botdb.set(f"whois:{m.from_user.id}", True)
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")

    if m.data == "ban" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        await m.edit_message_text(
            "• ارسل الآن ايدي المستخدم لحظره\n• للإلغاء ارسل الغاء ",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]
            ),
        )
        botdb.set(f"ban:{m.from_user.id}", True)
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")

    if m.data == "unban" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        await m.edit_message_text(
            "• ارسل الآن ايدي المستخدم لرفع حظره\n• للإلغاء ارسل الغاء ",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]
            ),
        )
        botdb.set(f"unban:{m.from_user.id}", True)
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")

    if m.data == "addadmin" and m.from_user.id == ownerID:
        await m.edit_message_text(
            "• ارسل الآن ايدي المستخدم لرفعه ادمن\n• للإلغاء ارسل الغاء ",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]
            ),
        )
        botdb.set(f"add:{m.from_user.id}", True)
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")

    if m.data == "remadmin" and m.from_user.id == ownerID:
        await m.edit_message_text(
            "• ارسل الآن ايدي المستخدم لرفعه ادمن\n• للإلغاء ارسل الغاء ",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]
            ),
        )
        botdb.set(f"rem:{m.from_user.id}", True)
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")

    if m.data == "back" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        # await m.answer("• تم الرجوع بنجاح والغاء كل شي ",show_alert=True)
        await m.edit_message_text(
            f"""
**• أهلاً بك ⌯ {m.from_user.mention} .
 — أليك لوحة الادمن ..
 — يمكنك من خلال اللوحة ان تتحكم بأعدادات البوت والرفع والتنزيل !
 — – — – — – — – — – — – —
 
- Join ...

**""",
            reply_markup=STARTKEY,
        )
        botdb.delete(f"broad:{m.from_user.id}")
        botdb.delete(f"whois:{m.from_user.id}")
        botdb.delete(f"ban:{m.from_user.id}")
        botdb.delete(f"add:{m.from_user.id}")
        botdb.delete(f"rem:{m.from_user.id}")
        botdb.delete(f"unban:{m.from_user.id}")

    if m.data == "stats" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        users = len(botdb.get("db" + token.split(":")[0])["users"])
        await m.answer(
            f"• احصائيات البوت ⌯ {users}", show_alert=True, cache_time=10
        )

    if m.data == "adminstats" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        admins = len(botdb.get("db" + token.split(":")[0])["admins"])
        await m.answer(
            f"• احصائيات الادمنية ⌯ {admins}\n• سيتم ارسال بيانات كل آدمن",
            show_alert=True,
            cache_time=60,
        )
        text = "- الادمنية:\n\n"
        count = 1
        for admin in botdb.get("db" + token.split(":")[0])["admins"]:
            if count == 101:
                break
            getUser = botdb.get(f"USER:{admin}")
            mention = getUser["mention"]
            id = getUser["id"]
            text += f"{count}) {mention} ~ (`{id}`)\n"
            count += 1
        text += "\n\n—"
        await m.message.reply(text, quote=True)

    if m.data == "bannedstats" and (
        m.from_user.id == ownerID
        or m.from_user.id in botdb.get("db" + token.split(":")[0])["admins"]
    ):
        bans = botdb.get("db" + token.split(":")[0])["banned"]
        if not bans:
            return await m.answer(
                "• لا يوجد محظورين", show_alert=True, cache_time=60
            )
        await m.answer(
            f"• احصائيات المحظورين ⌯ {len(bans)}\n• سيتم ارسال بيانات كل المحظورين",
            show_alert=True,
            cache_time=60,
        )
        text = "- المحظورين:\n\n"
        count = 1
        for banned in bans:
            if count == 101:
                break
            getUser = botdb.get(f"USER:{banned}")
            mention = getUser["mention"]
            id = getUser["id"]
            text += f"{count}) {mention} ~ (`{id}`)\n"
            count += 1
        text += "\n\n—"
        await m.message.reply(text, quote=True)


idle()
