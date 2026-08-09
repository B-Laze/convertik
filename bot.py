import os
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from docx2pdf import convert
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
    ".png": convert_word_to_pdf,
}
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







