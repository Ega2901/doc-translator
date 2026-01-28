# Версионирование и релизы

Версия задаётся в `pyproject.toml` в поле `[project] version`.

## Формат версий (Semantic Versioning)

- **MAJOR.MINOR.PATCH** (например, 1.2.3)
- MAJOR — несовместимые изменения API
- MINOR — новая функциональность с обратной совместимостью
- PATCH — исправления ошибок

## Как сделать релиз

1. Обновить версию в `pyproject.toml`:

   ```bash
   # Отредактировать вручную или через sed:
   # version = "0.1.0"  ->  version = "0.2.0"
   ```

2. Закоммитить и создать тег:

   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.2.0"
   git tag -a v0.2.0 -m "Release 0.2.0"
   git push origin main
   git push origin v0.2.0
   ```

3. (Опционально) Собрать пакет:

   ```bash
   uv build
   # Артефакты в dist/
   ```

## Просмотр текущей версии

```bash
# После установки пакета
python -c "import doc_translator; print(doc_translator.__version__)"
```
