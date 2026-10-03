import os
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from cloudflare import crear_registro, CloudflareError
from database import (
    init_db,
    dar_acceso as db_dar_acceso,
    quitar_acceso as db_quitar_acceso,
    acceso_activo,
    obtener_vencimiento,
    usuarios_activos,
)

BOT_TOKEN = os.getenv("8819531441:AAFtc82ROSVnt6taQylLDYpeFwlmCGdFY8Y")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "8823167645"))
BASE_DOMAIN = (os.getenv("BASE_DOMAIN") or "golbertvps.net.pe").strip().lower().rstrip(".")
VPS_IP = (os.getenv("VPS_IP") or "45.41.207.172").strip()

LIMA = ZoneInfo("America/Lima")

LABEL_RE = re.compile(
    r"^(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)

HOST_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\.?$",
    re.IGNORECASE,
)


def validar_config():
    faltantes = []

    for nombre, valor in {
        "8819531441:AAFtc82ROSVnt6taQylLDYpeFwlmCGdFY8Y": BOT_TOKEN,
        "TELEGRAM_ADMIN_ID": ADMIN_ID,
        "CF_API_TOKEN": os.getenv("CF_API_TOKEN"),
        "CF_ZONE_ID": os.getenv("CF_ZONE_ID"),
        "BASE_DOMAIN": BASE_DOMAIN,
        "VPS_IP": VPS_IP,
    }.items():
        if not valor:
            faltantes.append(nombre)

    if faltantes:
        raise RuntimeError(
            "Faltan variables en .env: " + ", ".join(faltantes)
        )


def es_admin(update: Update) -> bool:
    return bool(
        update.effective_user
        and update.effective_user.id == ADMIN_ID
    )


def fecha_peru(timestamp: int) -> str:
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(LIMA)
    return dt.strftime("%d/%m/%Y %I:%M %p")


async def verificar_acceso(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False

    if user.id == ADMIN_ID:
        return True

    if acceso_activo(user.id):
        return True

    await update.effective_message.reply_text(
        "❌ Tu acceso no está activo o ya venció.\n\n"
        f"🆔 Tu Telegram ID: {user.id}\n"
        "Solicita una renovación al administrador."
    )
    return False


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    texto = (
        "🤖 Bot DNS Cloudflare\n\n"
        f"🆔 Tu ID: {user_id}\n\n"
        "Comandos:\n"
        "/miid - Ver tu Telegram ID\n"
        "/estado - Ver tu acceso\n"
        "/sub nombre - Crear un A hacia la VPS\n"
        "/ns nombre ns1.dominio.com [ns2.dominio.com] - Delegar por NS\n"
    )

    if es_admin(update):
        texto += (
            "\n👑 Administración:\n"
            "/dar ID DIAS\n"
            "/quitar ID\n"
            "/usuarios\n"
        )

    await update.message.reply_text(texto)


async def miid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👤 {user.first_name}\n"
        f"🆔 Telegram ID: {user.id}"
    )


async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "👑 Administrador\nAcceso permanente."
        )
        return

    vencimiento = obtener_vencimiento(user_id)

    if not vencimiento:
        await update.message.reply_text(
            "❌ No tienes acceso registrado."
        )
        return

    ahora = int(time.time())

    if vencimiento <= ahora:
        await update.message.reply_text(
            "❌ Tu acceso venció.\n\n"
            f"📅 Venció: {fecha_peru(vencimiento)}"
        )
        return

    restante = vencimiento - ahora
    dias = restante // 86400
    horas = (restante % 86400) // 3600

    await update.message.reply_text(
        "✅ Acceso activo\n\n"
        f"⏳ Restante: {dias} días y {horas} horas\n"
        f"📅 Vence: {fecha_peru(vencimiento)}"
    )


async def dar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Uso:\n/dar TELEGRAM_ID DIAS\n\n"
            "Ejemplo:\n/dar 123456789 7"
        )
        return

    try:
        telegram_id = int(context.args[0])
        dias = int(context.args[1])

        if telegram_id <= 0 or not 1 <= dias <= 3650:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ ID o número de días inválido."
        )
        return

    vencimiento = db_dar_acceso(
        telegram_id,
        dias,
        ADMIN_ID,
    )

    await update.message.reply_text(
        "✅ Acceso activado\n\n"
        f"🆔 Usuario: {telegram_id}\n"
        f"➕ Días añadidos: {dias}\n"
        f"📅 Vence: {fecha_peru(vencimiento)}"
    )


async def quitar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Uso:\n/quitar TELEGRAM_ID"
        )
        return

    try:
        telegram_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Telegram ID inválido.")
        return

    db_quitar_acceso(telegram_id)

    await update.message.reply_text(
        "🚫 Acceso eliminado\n\n"
        f"🆔 Usuario: {telegram_id}"
    )


async def usuarios_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return

    rows = usuarios_activos()

    if not rows:
        await update.message.reply_text(
            "No hay usuarios activos."
        )
        return

    texto = "👥 USUARIOS ACTIVOS\n\n"

    for row in rows:
        texto += (
            f"🆔 {row['telegram_id']}\n"
            f"📅 {fecha_peru(row['expires_at'])}\n\n"
        )

    # Telegram tiene límite de tamaño de mensaje.
    await update.message.reply_text(texto[:4000])


async def sub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update):
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Uso:\n/sub nombre\n\n"
            "Ejemplo:\n/sub cliente01"
        )
        return

    etiqueta = context.args[0].strip().lower()

    if not LABEL_RE.fullmatch(etiqueta):
        await update.message.reply_text(
            "❌ Nombre inválido.\n"
            "Usa letras minúsculas, números y guiones."
        )
        return

    fqdn = f"{etiqueta}.{BASE_DOMAIN}"

    try:
        result = await crear_registro(
            "A",
            fqdn,
            VPS_IP,
            proxied=False,
        )

        await update.message.reply_text(
            "✅ Subdominio creado\n\n"
            f"Tipo: A\n"
            f"🌐 {result['name']}\n"
            f"🖥 {result['content']}\n"
            "☁️ DNS Only"
        )

    except CloudflareError as exc:
        await update.message.reply_text(
            f"❌ Cloudflare:\n{exc}"
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Error inesperado:\n{exc}"
        )


async def ns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso:\n"
            "/ns nombre ns1.dominio.com [ns2.dominio.com ...]\n\n"
            "Ejemplo:\n"
            "/ns tunel ns1.midns.com ns2.midns.com"
        )
        return

    etiqueta = context.args[0].strip().lower()
    nameservers = [
        item.strip().lower().rstrip(".")
        for item in context.args[1:]
    ]

    if not LABEL_RE.fullmatch(etiqueta):
        await update.message.reply_text(
            "❌ Nombre de subdominio inválido."
        )
        return

    if len(nameservers) > 7:
        await update.message.reply_text(
            "❌ Usa como máximo 7 nameservers."
        )
        return

    for ns in nameservers:
        if not HOST_RE.fullmatch(ns):
            await update.message.reply_text(
                f"❌ Nameserver inválido: {ns}"
            )
            return

    fqdn = f"{etiqueta}.{BASE_DOMAIN}"
    creados = []

    try:
        for servidor in nameservers:
            result = await crear_registro(
                "NS",
                fqdn,
                servidor,
            )
            creados.append(result["content"])

        await update.message.reply_text(
            "✅ Delegación NS creada\n\n"
            f"🌐 {fqdn}\n"
            + "\n".join(f"➡️ {ns}" for ns in creados)
        )

    except CloudflareError as exc:
        await update.message.reply_text(
            "❌ Cloudflare rechazó la operación.\n\n"
            f"{exc}\n\n"
            "Si ese nombre ya tiene A/CNAME, elimínalo antes de delegarlo por NS."
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Error inesperado:\n{exc}"
        )


def main():
    validar_config()
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("miid", miid_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))

    app.add_handler(CommandHandler("sub", sub_cmd))
    app.add_handler(CommandHandler("ns", ns_cmd))

    app.add_handler(CommandHandler("dar", dar_cmd))
    app.add_handler(CommandHandler("quitar", quitar_cmd))
    app.add_handler(CommandHandler("usuarios", usuarios_cmd))

    print("Bot iniciado.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
      
