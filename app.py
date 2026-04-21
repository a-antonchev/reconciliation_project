import os
import tempfile
import io
import traceback

from google import genai
import pandas as pd
import streamlit as st

from constants import API_KEY
from parser import parse_file
from extractor import extract_specification
from matcher import reconcile
from models import MatchStatus

global_client = genai.Client(api_key=API_KEY)

st.set_page_config(
    page_title="AI Сверка спецификаций",
    page_icon=":robot_face:",
    layout="wide",
)
st.title("🤖 AI Сверка спецификаций")
st.markdown(
    "Загрузите два документа (Word или Excel), и искусственный интеллект найдет все расхождения."
)

# проверка API ключа
if not API_KEY:
    st.error(
        "⚠️ Не найден GEMINI_API_KEY. Пожалуйста, установите переменную окружения."
    )
    st.stop()

# --- UI: загрузка файлов ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Эталон (Базовый документ)")
    baseline_file = st.file_uploader(  # -> объект класса streamlit.runtime.uploaded_file_manager.UploadedFile
        "Загрузите файл Эталона", type=["docx", "xlsx", "xls"], key="base"
    )

with col2:
    st.subheader("📄 Заявка (Проверяемый документ)")
    target_file = st.file_uploader(
        "Загрузите файл Заявки", type=["docx", "xlsx", "xls"], key="target"
    )


# `parser.py` ожидает путь к файлу на диске - создаем вспомогательную функцию
def save_uploaded_file(uploaded_file) -> str:
    """
    Сохраняет загруженный пользователем файл в временную директорию.
    """
    # uploaded_file.name -> str - оригинальное имя файла
    # это атрибут объекта streamlit.runtime.uploaded_file_manager.UploadedFile
    suffix = os.path.splitext(uploaded_file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        # `getbuffer()` - Streamlit рекомендует этот способ для быстрого чтения загруженных файлов без лишнего копирования в памяти
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


# вспомогательная функция для генерации Excel
def generate_excel(results) -> bytes:
    # создаем список словарей из списка Pydantic-объектов
    # mode='json' -> слить объект в словарь, где все значения безопасны для JSON (то есть Enum преврати в строки)
    data = [row.model_dump(mode="json") for row in results]
    # создаем dataframe из списка словарей
    df = pd.DataFrame(data)
    # переименовываем столбцы
    df = df.rename(
        columns={
            "status": "Статус",
            "baseline_sku": "Артикул (Эталон)",
            "baseline_name": "Наименование (Эталон)",
            "baseline_description": "Описание (Эталон)",
            "baseline_qty": "Кол-во (Эталон)",
            "baseline_unit": "Ед.изм. (Эталон)",
            "target_sku": "Артикул (Заявка)",
            "target_name": "Наименование (Заявка)",
            "target_description": "Описание (Заявка)",
            "target_qty": "Кол-во (Заявка)",
            "target_unit": "Ед.изм. (Заявка)",
            "discrepancy_notes": "Заметки системы",
        }
    )
    # записываем в память
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Отчет о сверке", index=False)

        # автоширина столбцов
        # worksheet = writer.sheets["Отчет о сверке"]
        # for i, col in enumerate(df.columns):
        #     column_length = (
        #         max(df[col].astype(str).map(len).max(), len(col)) + 2
        #     )
        #     worksheet.set_column(
        #         i, i, min(column_length, 50)
        #     )  # ограничиваем ширину столбца 50 символов

        worksheet = writer.sheets["Отчет о сверке"]
        for i, col in enumerate(df.columns):
            # 1. Используем .str.len() вместо .map(len) - это безопаснее для пустых значений
            content_lengths = df[col].astype(str).str.len()
            max_content_len = content_lengths.max()

            # 2. Защита от float (NaN): если колонка пустая, max() вернет NaN
            if pd.isna(max_content_len):
                max_content_len = 0

            # 3. Вычисляем итоговую ширину, гарантированно работая с целыми числами и строками
            column_length = max(int(max_content_len), len(str(col))) + 2

            worksheet.set_column(i, i, min(column_length, 50))

    # здесь контекстный менеджер закрывается и вызывает метод writer.close()

    return output.getvalue()


# --- ОСНОВНАЯ ЛОГИКА ---
if st.button("🚀 Запустить сверку", type="primary", width="stretch"):
    if not baseline_file or not target_file:
        st.warning("Пожалуйста, загрузите оба файлы.")
    else:
        try:
            # сохраняем загруженные файлы во временную директорию
            base_path = save_uploaded_file(baseline_file)
            target_path = save_uploaded_file(target_file)

            # используем `st.status` для отображения прогресса
            with st.status("Выполняю сверку...", expanded=True) as status:
                st.write("⏳ Чтение документов...")
                base_md = parse_file(base_path)
                target_md = parse_file(target_path)

                st.write("🧠 Извлечение данных через AI (Эталон)...")
                base_spec = extract_specification(
                    base_md, client=global_client
                )

                st.write("🧠 Извлечение данных через AI (Заявка)...")
                target_spec = extract_specification(
                    target_md, client=global_client
                )

                st.write("🔍 Поиск расхождений...")
                report = reconcile(
                    base_spec.items, target_spec.items, client=global_client
                )

                status.update(
                    label="✅ Сверка завершена!",
                    state="complete",
                    expanded=False,
                )

            # удаляем временные файлы
            if os.path.exists(base_path):
                os.remove(base_path)
            if os.path.exists(target_path):
                os.remove(target_path)

            # --- ВЫВОД РЕЗУЛЬТАТОВ ---
            st.success(
                f"Обработано позиций: Эталон ({len(base_spec.items)}), Заявка ({len(target_spec.items)})"
            )

            # генерируем Excel-файл
            excel_data = generate_excel(report)

            # кнопка скачивания
            st.download_button(
                label="📥 Скачать отчет (Excel)",
                data=excel_data,
                file_name="reconciliation_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

            # показываем превью на экране
            st.subheader("Предварительный просмотр")

            # для превью сделаем датафрейм чуть проще - сбрасываем модель в словарь
            preview_df = pd.DataFrame(
                [r.model_dump(mode="json") for r in report]
            )

            # подсвечиваем проблемные строки цветом
            def color_rows(row):
                if row["status"] == MatchStatus.PERFECT_MATCH.value:
                    return ["background-color: #d4edda"] * len(row)  # зеленый
                elif row["status"] == MatchStatus.PARTIAL_MATCH.value:
                    return ["background-color: #fff3cd"] * len(row)  # желтый
                else:
                    return ["background-color: #f8d7da"] * len(row)  # красный

            st.dataframe(
                preview_df.style.apply(color_rows, axis=1),
                width="stretch",
            )

        except Exception as e:
            st.error("Произошла ошибка во время обработки!")

            full_traceback = traceback.format_exc()
            with st.expander("Технические детали для разработчика"):
                st.code(full_traceback, language="python")
