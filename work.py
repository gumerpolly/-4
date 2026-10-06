# %% [markdown]
# # ЛР4: контейнер MySQL в Docker + подключение из Python
# 
# Тема базы данных: **книжный магазин** — таблица `books` (id, название, автор, год издания, цена).
# 
# Порядок работы: сначала выполните команды Docker из части 1 в терминале, затем запускайте ячейки тетрадки сверху вниз.

# %% [markdown]
# ## Часть 1. Запуск MySQL в Docker
# 
# Команды выполняются в терминале (PowerShell / bash), не в тетрадке.
# 
# ```bash
# # 1. Создаём именованный volume — здесь MySQL будет хранить файлы базы
# docker volume create mysql_lab4_data
# 
# # 2. Запускаем контейнер
# docker run -d \
#   --name mysql-lab4 \
#   -e MYSQL_ROOT_PASSWORD=rootpass \
#   -p 3306:3306 \
#   -v mysql_lab4_data:/var/lib/mysql \
#   mysql:8.0
# ```
# 
# В PowerShell вместо `\` в конце строк используйте обратный апостроф `` ` `` или напишите всё в одну строку:
# 
# ```
# docker run -d --name mysql-lab4 -e MYSQL_ROOT_PASSWORD=rootpass -p 3306:3306 -v mysql_lab4_data:/var/lib/mysql mysql:8.0
# ```
# 
# **Проверка, что всё работает:**
# 
# ```bash
# docker ps                                   # контейнер в статусе Up
# docker logs mysql-lab4                      # в конце: "ready for connections" ... port: 3306
# docker exec -it mysql-lab4 mysqladmin ping -uroot -prootpass   # mysqld is alive
# docker exec -it mysql-lab4 mysql -uroot -prootpass -e "SELECT VERSION();"
# ```
# 
# Если порт 3306 занят (например, у вас уже установлен MySQL), используйте `-p 3307:3306` и поменяйте `port` в ячейке с настройками ниже на `3307`.

# %% [markdown]
# ## Часть 2. Подключение из Python
# 
# Используем драйвер `mysql-connector-python` (официальный от Oracle, без лишних настроек работает с паролями MySQL 8).

# %%
%pip install mysql-connector-python

# %%
import time
import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "rootpass",
}
DB_NAME = "bookstore"


def connect(database=None, attempts=15, delay=2):
    """Подключается к MySQL, повторяя попытки, пока сервер в контейнере стартует."""
    config = dict(DB_CONFIG)
    if database:
        config["database"] = database
    for i in range(1, attempts + 1):
        try:
            conn = mysql.connector.connect(**config)
            print(f"Подключено к MySQL {conn.server_info} (попытка {i})")
            return conn
        except Error as e:
            print(f"Попытка {i}: сервер ещё не готов ({e.msg}), ждём {delay} с...")
            time.sleep(delay)
    raise RuntimeError("Не удалось подключиться к MySQL")


conn = connect()
cur = conn.cursor()

# %% [markdown]
# ## Часть 3. CRUD
# 
# ### 3.1 Создание базы данных

# %%
cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
cur.execute(f"USE {DB_NAME}")
cur.execute("SHOW DATABASES")
print([row[0] for row in cur.fetchall()])

# %% [markdown]
# ### 3.2 Создание таблицы
# 
# Атрибуты: `title`, `author`, `year`, `price`

# %%
cur.execute("DROP TABLE IF EXISTS books")
cur.execute("""
    CREATE TABLE books (
        id     INT AUTO_INCREMENT PRIMARY KEY,
        title  VARCHAR(200)  NOT NULL,
        author VARCHAR(100)  NOT NULL,
        year   INT           NOT NULL,
        price  DECIMAL(8, 2) NOT NULL
    )
""")
cur.execute("DESCRIBE books")
for row in cur.fetchall():
    print(row)

# %% [markdown]
# ### 3.3 Вставка нескольких записей через `executemany()`
# 

# %%
books = [
    ("Мастер и Маргарита",      "Михаил Булгаков",    1967, 650.00),
    ("Преступление и наказание", "Фёдор Достоевский",  1866, 480.00),
    ("Война и мир",              "Лев Толстой",        1869, 990.00),
    ("Пикник на обочине",        "Стругацкие",         1972, 420.00),
    ("1984",                     "Джордж Оруэлл",      1949, 550.00),
    ("Мы",                       "Евгений Замятин",    1924, 390.00),
]

sql_insert = "INSERT INTO books (title, author, year, price) VALUES (%s, %s, %s, %s)"
cur.executemany(sql_insert, books)
conn.commit()
print("Вставлено записей:", cur.rowcount)

# %% [markdown]
# ### 3.4 Вывод всех записей

# %%
def print_books(cursor, title="Все книги"):
    cursor.execute("SELECT id, title, author, year, price FROM books ORDER BY id")
    rows = cursor.fetchall()
    print(f"{'id':<4}{'Название':<28}{'Автор':<22}{'Год':<6}{'Цена':>8}")
    for r in rows:
        print(f"{r[0]:<4}{r[1]:<28}{r[2]:<22}{r[3]:<6}{r[4]:>8}")


print_books(cur)

# %% [markdown]
# ### 3.5 SELECT с фильтром и сортировкой
# 
# Книги, изданные после 1900 года, от самой дорогой к самой дешёвой.

# %%
min_year = 1900
cur.execute(
    "SELECT title, author, year, price FROM books WHERE year > %s ORDER BY price DESC",
    (min_year,)
)
for row in cur.fetchall():
    print(row)

# %% [markdown]
# ### 3.6 Обновление одной записи

# %%
cur.execute(
    "UPDATE books SET price = %s WHERE title = %s",
    (720.00, "Мастер и Маргарита")
)
conn.commit()
print("Обновлено строк:", cur.rowcount)

# %% [markdown]
# ### 3.7 Удаление одной записи

# %%
cur.execute("DELETE FROM books WHERE title = %s", ("Мы",))
conn.commit()
print("Удалено строк:", cur.rowcount)

# %% [markdown]
# ### 3.8 Вывод

# %%
print_books(cur, "Итоговое состояние таблицы")
cur.close()
conn.close()

# %% [markdown]
# # 4. Проверка volume

# %%
conn = connect(database=DB_NAME)
cur = conn.cursor()
print_books(cur, "Данные после пересоздания контейнера")
cur.close()
conn.close()


