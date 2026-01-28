# Настройка приватного репозитория на GitHub

## 1. Создать репозиторий на GitHub

1. Откройте [github.com/new](https://github.com/new).
2. **Repository name:** `doc-translator` (или другое имя).
3. **Visibility:** выберите **Private**.
4. **Не** ставьте галочки "Add a README", "Add .gitignore", "Choose a license" — репозиторий должен быть пустым.
5. Нажмите **Create repository**.

## 2. Привязать локальный репозиторий и отправить код

В терминале выполните (подставьте свой логин и имя репозитория):

```bash
cd /Users/egor/doc_translator

# Добавить удалённый репозиторий
git remote add origin https://github.com/YOUR_USERNAME/doc-translator.git

# Отправить ветку main и теги
git push -u origin main
git push origin v0.1.0
```

Если используете SSH:

```bash
git remote add origin git@github.com:YOUR_USERNAME/doc-translator.git
git push -u origin main
git push origin v0.1.0
```

## 3. Дальнейшая работа

- Обычные коммиты: `git add ...`, `git commit -m "..."`, `git push`.
- Новый релиз: обновите версию в `pyproject.toml`, закоммитьте, создайте тег `vX.Y.Z` и выполните `git push origin vX.Y.Z`.
- Подробнее см. [RELEASING.md](../RELEASING.md).
