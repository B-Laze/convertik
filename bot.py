import io
import os
import asyncio

from io import BytesIO
from pypdf import PdfReader, PdfWriter
from aiogram import Bot, Dispatcher, F, types, Router
from aiogram.types import (
    BufferedInputFile,
    Message,
    KeyboardButton,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery)
from aiogram.fsm.context import FSMContext
from aiogram.filters import (CommandStart, Command)
from docx2pdf import convert
from PIL import Image
from dotenv import load_dotenv
from rembg import remove

from states import SplitPDF, RotatePDF, MergePDF, rotate_kb, merge_kb
from pdf_utils import extract_pdf_pages, rotate_pdf_pages, merge_pdfs, parse_page_range

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

FILE_CACE = {}

def remove_bg_from_bytes(input_bytes: bytes) -> bytes:
    input_image = Image.open(io.BytesIO(input_bytes))
    output_image = remove(input_image)
    output_buffer = io.BytesIO()
    output_image.save(output_buffer, format="PNG")
    return output_buffer.getvalue()

def convert_image_bytes(input_bytes: bytes, target_format: str) -> bytes:
    image = Image.open(io.BytesIO(input_bytes))

    target_format = target_format.upper()
    if target_format == "JPG":
        target_format = "JPEG"

    if target_format in ["JPEG", "PDF"] and image.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = background
    elif image.mode != "RGB" and target_format == "JPEG":
        image = image.convert("RGB")

    output_buffer = io.BytesIO()
    image.save(output_buffer, format=target_format)
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

def get_actions_kb(file_key: str, is_image: bool = True) -> InlineKeyboardMarkup:
    buttons = []

    if is_image:
        buttons.append([
            InlineKeyboardButton(text="Убрать фон", callback_data=f"action:action:{file_key}")
        ])
        buttons.append([
            InlineKeyboardButton(text="В PDF", callback_data=f"action:pdf:{file_key}"),
            InlineKeyboardButton(text="В JPG", callback_data=f"action:jpg:{file_key}"),
            InlineKeyboardButton(text="В PNG", callback_data=f"action:png:{file_key}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="В PDF", callback_data=f"action:pdf:{file_key}")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)



@router.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет! Я твой помощник по обработке и конвертации файлов.\n\n"
        "<b>Команды для PDF:</b>\n"
        "/split — Извлечь страницы из PDF\n"
        "/rotate — Повернуть страницы PDF\n"
        "/merge — Объединить несколько PDF в один\n\n"
        "Или просто отправь мне фото/документ Word для конвертации.",
        parse_mode="HTML"

    )


@router.message(Command("split"))
async def cmd_split(message: Message, state: FSMContext):
    await state.set_state(SplitPDF.waiting_for_file)
    await message.answer("Отправь PDF-файл, из которого нужно извлечь страницы:")


@router.message(SplitPDF.waiting_for_file, F.document)
async def process_split_file(message: Message, state: FSMContext, bot: Bot):
    if not message.document.file_name.lower().endswith('.pdf'):
        await message.answer("Пожалуйста, отправь файл в формате PDF.")
        return

    file_bytes = await bot.download(message.document)
    await state.update_data(pdf_bytes=file_bytes.read())
    await state.set_state(SplitPDF.waiting_for_pages)

    await message.answer(
        "Укажи страницы для извлечения.\n"
        "Формат: `1-3, 5, 8-10`",
        parse_mode="Markdown"
    )


@router.message(SplitPDF.waiting_for_pages, F.text)
async def process_split_pages(message: Message, state: FSMContext):
    data = await state.get_data()
    pdf_bytes = data["pdf_bytes"]
    page_range_str = message.text

    try:
        output_bytes = extract_pdf_pages(pdf_bytes, page_range_str)
        document = BufferedInputFile(output_bytes, filename="split_result.pdf")
        await message.answer_document(document=document, caption="Готово!")
        await state.clear()
    except Exception as e:
        await message.answer("Ошибка при обработке диапазона страниц. Проверь правильность ввода (например: 1-3, 5).")


@router.message(Command("rotate"))
async def cmd_rotate(message: Message, state: FSMContext):
    await state.set_state(RotatePDF.waiting_for_file)
    await message.answer("Отправьте PDF-файл для поворота страниц:")


@router.message(RotatePDF.waiting_for_file, F.document)
async def process_rotate_file(message: Message, state: FSMContext, bot: Bot):
    if not message.document.file_name.endswith('.pdf'):
        await message.answer("Отправьте PDF-файл.")
        return

    file_bytes = await bot.download(message.document)
    await state.update_data(pdf_bytes=file_bytes.read())
    await state.set_state(RotatePDF.waiting_for_angle)

    await message.answer("Выберите угол поворота по часовой стрелке:", reply_markup=rotate_kb)


@router.callback_query(RotatePDF.waiting_for_angle, F.data.startswith("rotate_"))
async def process_rotate_angle(callback: CallbackQuery, state: FSMContext):
    degrees = int(callback.data.split("_")[1])
    await state.update_data(degrees=degrees)
    await state.set_state(RotatePDF.waiting_for_pages)

    await callback.message.edit_text(
        "Введите страницы для поворота (например: `1-3, 5`) или напишите `все`:",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(RotatePDF.waiting_for_pages, F.text)
async def process_rotate_pages(message: Message, state: FSMContext):
    data = await state.get_data()
    pdf_bytes = data["pdf_bytes"]
    degrees = data["degrees"]
    page_range_str = message.text.strip()

    try:
        output_bytes = rotate_pdf_pages(pdf_bytes, degrees, page_range_str)
        document = BufferedInputFile(output_bytes, filename="rotated_result.pdf")
        await message.answer_document(document=document, caption="Страницы повернуты!")
        await state.clear()
    except Exception:
        await message.answer("Ошибка при обработке страниц. Укажите корректный диапазон или слово 'все'.")


@router.message(Command("merge"))
async def cmd_merge(message: Message, state: FSMContext):
    await state.set_state(MergePDF.waiting_for_files)
    await state.update_data(files=[])
    await message.answer(
        "Отправляйте PDF-файлы по одному в том порядке, в котором их нужно склеить.\n"
        "Когда закончите, нажмите кнопку «✅ Склеить файлы».",
        reply_markup=merge_kb
    )


@router.message(MergePDF.waiting_for_files, F.document)
async def process_merge_file(message: Message, state: FSMContext, bot: Bot):
    if not message.document.file_name.endswith('.pdf'):
        await message.answer("Принимаются только PDF-файлы.")
        return

    file_bytes = await bot.download(message.document)
    data = await state.get_data()
    files_list = data.get("files", [])
    files_list.append(file_bytes.read())

    await state.update_data(files=files_list)
    await message.answer(f"Файл добален! Всего файлов в очереди: {len(files_list)}")


@router.message(MergePDF.waiting_for_files, F.text == "✅ Склеить файлы")
async def process_merge_done(message: Message, state: FSMContext):
    data = await state.get_data()
    files_list = data.get("files", [])

    if len(files_list) < 2:
        await message.answer("Для объединения нужно отправить минимум 2 файла.")
        return

    output_bytes = merge_pdfs(files_list)
    document = BufferedInputFile(output_bytes, filename="merged_result.pdf")

    await message.answer_document(
        document=document,
        caption="Файлы успешно объединены!",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()


@router.message(MergePDF.waiting_for_files, F.text == "❌ Отмена")
async def process_merge_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Операция отменена.", reply_markup=ReplyKeyboardRemove())

@router.message(F.photo)
async def handle_photo(message: Message):
    photo = message.photo[-1]
    file_key = str(message.message_id)

    FILE_CACE[file_key] = {"file_id": photo.file_id, "ext": ".jpg", "is_image": True}

    await message.answer(
        "Что будем делать с этой картинкой?",
        reply_markup=get_actions_kb(file_key, is_image=True),
    )

@router.message(F.document)
async def handle_document(message: types.Message):
    document = message.document
    file_name = document.file_name or "file"
    file_ext = os.path.splitext(file_name)[1].lower()

    if file_ext not in CONVERTERS:
        allowed = ", ".join(CONVERTERS.keys())
        await message.answer(
            f"❌ Формат `{file_ext}` не поддерживается.\nДоступные: {allowed}",
            parse_mode="Markdown",
        )
        return

    file_key = str(message.message_id)
    is_image = file_ext in [".jpg", ".jpeg", ".png"]
    FILE_CACE[file_key] = {
        "file_id": document.file_id,
        "ext": file_ext,
        "file_name": file_name,
        "is_image": is_image,
    }

    await message.answer(
        f"Файл <b>{file_name}</b> получен. Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_actions_kb(file_key, is_image=is_image),
    )

@router.callback_query(F.data.startswith("action:"))
async def process(callback: CallbackQuery, bot: Bot):
    _, action, file_key = callback.data.split(":")
    file_data = FILE_CACE.get(file_key)

    if not file_data:
        await callback.answer("⚠️ Данные файла устарели, отправьте его снова.", show_alert=True)
        return

    await callback.answer("Обрабатываю...")
    await callback.message.edit_text("⏳ Выполняю обработку файла...")

    try:
        file_info = await bot.get_file(file_data["file_id"])
        raw_name = file_data.get("file_name", f"file_{file_key}")
        base_name = os.path.splitext(raw_name)[0]

        # 1. Удаление фона
        if action == "action":
            file_io = io.BytesIO()
            await bot.download_file(file_info.file_path, file_io)
            result_bytes = await asyncio.to_thread(remove_bg_from_bytes, file_io.getvalue())

            output_file = BufferedInputFile(result_bytes, filename=f"{base_name}_action.png")
            await callback.message.answer_document(
                document=output_file, caption="✨ Фон успешно удален!"
            )

        # 2. Обработка изображений (В PDF, JPG, PNG)
        elif file_data["is_image"]:
            file_io = io.BytesIO()
            await bot.download_file(file_info.file_path, file_io)

            result_bytes = await asyncio.to_thread(
                convert_image_bytes, file_io.getvalue(), action
            )

            ext = action if action != "jpeg" else "jpg"
            output_file = BufferedInputFile(result_bytes, filename=f"{base_name}.{ext}")
            await callback.message.answer_document(
                document=output_file, caption=f"✨ Готово! Файл сконвертирован в {action.upper()}."
            )

        # 3. Обработка Word документов в PDF (через дисковый буфер)
        elif action == "pdf" and file_data["ext"] in [".docx", ".doc"]:
            input_path = os.path.abspath(f"temp_{file_key}{file_data['ext']}")
            output_path = os.path.abspath(f"temp_{file_key}.pdf")

            try:
                await bot.download_file(file_info.file_path, input_path)
                await asyncio.to_thread(convert_word_to_pdf, input_path, output_path)

                pdf_file = types.FSInputFile(output_path, filename=f"{base_name}.pdf")
                await callback.message.answer_document(
                    document=pdf_file, caption="✨ Готово! Документ сконвертирован в PDF."
                )
            finally:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)

    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при обработке: {e}")
    finally:
        FILE_CACE.pop(file_key, None)


async def main():
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())







