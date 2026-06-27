import asyncio
import sys
import os

# Добавляем текущую директорию в PYTHONPATH для корректного импорта модулей app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import SessionLocal
from app.parsers.archive_parser import ArchiveProcessor
from app.api.routes.admin import process_documents_task

async def upload_zip_cli(zip_path: str):
    if not os.path.exists(zip_path):
        print(f"Ошибка: Файл '{zip_path}' не существует.")
        sys.exit(1)
        
    if not zip_path.endswith(".zip"):
        print("Ошибка: Допускаются только ZIP-архивы.")
        sys.exit(1)
        
    print(f"Чтение ZIP-архива: {zip_path}...")
    with open(zip_path, "rb") as f:
        content = f.read()
        
    async with SessionLocal() as db:
        processor = ArchiveProcessor(db)
        documents_to_process = await processor.process_zip(content)
        
        if not documents_to_process:
            print("Предупреждение: Не найдено поддерживаемых файлов или партнеров.")
            return
            
        print(f"Найдено документов для обработки: {len(documents_to_process)}")
        print("Запуск процесса парсинга и сопоставления...")
        
        # Запускаем обработку напрямую (синхронно по отношению к CLI)
        await process_documents_task(documents_to_process)
        print("Обработка успешно завершена!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python cli_upload.py <путь_к_zip_архиву>")
        sys.exit(1)
        
    zip_filepath = sys.argv[1]
    asyncio.run(upload_zip_cli(zip_filepath))
