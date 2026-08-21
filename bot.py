import io
import os
import asyncio
from email.mime import image
from unittest import result

from aiogram import (Bot, Dispatcher, F, types, Router)
from aiogram.types import BufferedInputFile, Message
from aiogram.filters import CommandStart
from docx2pdf import convert
from PIL import Image
from dotenv import load_dotenv
from rembg import remove


load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

dp.include_router(router)

def remove_bg_from_bytes(input_bytes: bytes) -> bytes:
    input_image = Image.open(io.BytesIO(input_bytes))
    output_image = remove(input_image)
    output_buffer = io.BytesIO()
    output_image.save(output_buffer, format="PNG")
    return output_buffer.getvalue()



def convert_word_to_pdf(input_path: str, output_path: str):
    convert(input_path, output_path)

def convert_image_to_pdf(input_path: str, output_path: str):
    image = Image.open(input_path)
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(output_path,"PDF", resolution=100.0)


CONVERTERS = {
    ".docx": convert_word_to_pdf,
    ".doc": convert_word_to_pdf,
    ".jpg": convert_image_to_pdf,
    ".jpeg": convert_image_to_pdf,
    ".png": convert_image_to_pdf,
}

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    await message.answer(
        f"Обрабатываю изображение, убираю фон...\n\n"
    )
    photo = message.photo[-1]
    file_io = io.BytesIO()
    await bot.download(photo, destination=file_io)
    input_bytes = file_io.getvalue()
    result_bytes = remove_bg_from_bytes(input_bytes)
    document = BufferedInputFile(result_bytes, filename="no_background.png")
    await message.answer_document(
        document=document,
        caption="Готово! Фон удален.")


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    formats =", ".join(CONVERTERS.keys())
    await message.answer(
        f"Привет! я ботик конвертер)\n\n"
        f"Пришли мне файлик и я переведу его в PDF.\n"
        f"Поддерживаемые форматы: {formats}"
    )

@dp.message(F.document)
async def handle_document(message: types.Message):
    document = message.document
    file_name = document.file_name
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in CONVERTERS:
        allowed = ",".join(CONVERTERS.keys())
        await message.answer(f"❌ Формат `{file_ext}` не поддерживается.\nДоступные: {allowed}")
        return

    status_msg = await message.answer("⏳ Скачиваю и конвертирую файл, подожди, котик...")
    input_path = os.path.abspath(f"temp_{document.file_id}{file_ext}")
    output_path = os.path.abspath(f"temp_{document.file_id}.pdf")

    try:
        file_info = await bot.get_file(document.file_id)
        await bot.download_file(file_info.file_path, input_path)

        converter_func = CONVERTERS[file_ext]

        await asyncio.to_thread(converter_func, input_path, output_path)

        original_name_with_ext = os.path.splitext(file_name)[0]
        result_filename = f"{original_name_with_ext}.pdf"
        pdf_file = types.FSInputFile(output_path,filename=result_filename)
        await message.answer_document(pdf_file)

    except Exception as e:
        await message.answer(f"⚠️ Произошла ошибочка при конвертации: {e}")

    finally:
        await status_msg.delete()
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

async def main():
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())







