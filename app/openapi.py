TAG_AUTH = "Авторизация"
TAG_USERS = "Пользователи"
TAG_ROLES = "Роли"
TAG_DISCIPLINES = "Дисциплины"
TAG_TOURNAMENTS = "Турниры"
TAG_PARTICIPANTS = "Участники"
TAG_REGISTRATIONS = "Регистрации"
TAG_QR = "QR-коды"
TAG_MATCHES = "Матчи"
TAG_AUDIT = "Аудит"
TAG_PREDICT = "Прогноз посещаемости"
TAG_EMPLOYEES = "Сотрудники"

OPENAPI_TAGS = [
    {"name": TAG_AUTH, "description": "Регистрация, вход, выход, текущий пользователь."},
    {"name": TAG_USERS, "description": "Учётные записи (CRUD). Только администратор."},
    {"name": TAG_ROLES, "description": "Список ролей системы. Только персонал."},
    {"name": TAG_DISCIPLINES, "description": "Дисциплины турниров (CS2, Dota 2, Valorant и т.д.)."},
    {"name": TAG_TOURNAMENTS, "description": "Турниры: создание, редактирование, активация."},
    {"name": TAG_PARTICIPANTS, "description": "Участники (игроки): профили, уровни."},
    {"name": TAG_REGISTRATIONS, "description": "Регистрации на турниры."},
    {"name": TAG_QR, "description": "Генерация и валидация QR-кодов для прохода на арену."},
    {"name": TAG_MATCHES, "description": "Результаты матчей."},
    {"name": TAG_AUDIT, "description": "Журнал аудита (действия пользователей)."},
    {"name": TAG_PREDICT, "description": "Прогноз посещаемости турнира (ИИ-модуль)."},
    {"name": TAG_EMPLOYEES, "description": "Сотрудники арены (судьи, организаторы)."},
]
