# Worked examples — PostgreSQL internals (Rogov, «PostgreSQL 18 изнутри»)

These show *form*: how to phrase, split and cover a topic. *What* to card is decided by
`interview-filter.md`: an identifier or parameter card below is a syntax demo, not a hint to
card every parameter. The facts are standard PostgreSQL
behaviour, but when making real cards, ground every card in the user's copy of the book and use
its terminology and section titles. Cards are in Russian because that's the user's card language;
the patterns transfer to any language.

## Contents
1. Anti-pattern gallery (bad → better)
2. Part I — Isolation and MVCC (snapshots, HOT, vacuum, freezing)
3. Part II — Buffer cache and WAL
4. Part III — Locks
5. Part IV — Query execution and statistics
6. Part V — Index types
7. PostgreSQL 18 changes

---

## 1. Anti-pattern gallery

### Vague stem
Bad:
```
Как карта видимости помогает index-only scan?
?
Если страница all-visible, не нужно идти в таблицу проверять видимость строки
```
Better: see the 7-card set in SKILL.md §2 (cause → condition → symptom → actor → reset →
scenario → cloze).

### Enumeration on the back
Bad:
```
Что входит в снимок данных?
?
xmin, xmax и список активных транзакций xip
```
Better — one card per component, each asking what that component *does*:
```
Снимок: изменения транзакций с номером меньше какого значения точно завершены?
?
Меньше `xmin` снимка — наименьшего номера транзакции, активной в момент снимка.

Снимок: изменения транзакций с номером начиная с какого значения не видны?
?
Начиная с `xmax` снимка — номера, следующего за последней завершённой транзакцией.

Зачем снимку список `xip`, если есть границы `xmin` и `xmax`?
?
Транзакции между `xmin` и `xmax` могли быть ещё активны в момент снимка — их изменения не видны.
```

### Yes/no
Bad:
```
Уменьшает ли обычный VACUUM размер файла таблицы?
?
Нет
```
Better — ask for what actually happens:
```
Что обычный `VACUUM` делает с местом, освобождённым от мёртвых версий строк?
?
Отмечает его в карте свободного пространства для повторного использования; файл обычно не уменьшается.
↳ Отрезать может только полностью пустые страницы в конце файла; сжать таблицу — `VACUUM FULL` (перезапись).
```

### Definition dump
Bad:
```
Что такое HOT-обновление?
?
Это оптимизация, при которой если не меняются индексированные столбцы и на странице есть место, новая версия
кладётся на ту же страницу, индексы не обновляются, а старые версии потом удаляются внутристраничной очисткой...
```
Better — split by lens (condition / benefit / knob):
```
При каком условии `UPDATE` может выполниться как HOT-обновление?
?
Не меняется ни один проиндексированный столбец, и новая версия помещается на ту же страницу.

Что экономит HOT-обновление по сравнению с обычным?
?
Не создаются новые индексные записи: индекс по-прежнему указывает на начало HOT-цепочки.

Какой параметр таблицы оставляет на страницах запас места, чтобы обновления чаще были HOT?
?
`fillfactor`
```

### Answer leak
Bad: `Какой бит карты видимости означает, что все версии на странице видимы всем снимкам?::all-visible`
(the question practically spells the answer). Better: ask for a consequence or the actor —
«Какой процесс обычно устанавливает …», «Что index-only scan делает, если бит не установлен?».

### Ambiguous out of context
Bad: `Почему это происходит?::Транзакция держит снимок` (relies on a heading).
Better: `Почему долгая транзакция мешает VACUUM очищать таблицы?::Её снимок держит горизонт: мёртвые версии ещё могут быть ей видны`.

---

## 2. Part I — Isolation and MVCC

Scenario (applied understanding):
```
В системе висит транзакция, открытая 6 часов назад. Почему растут таблицы, которые активно обновляются?
?
Очистка не может удалить версии строк, которые ещё могут быть видны её снимку: горизонт очистки не сдвигается.
↳ Смотреть `backend_xmin` в `pg_stat_activity`.
```

Mechanism + why:
```
Почему в PostgreSQL нужна заморозка версий строк?
?
Номера транзакций 32-битные и идут по кругу; без заморозки старые версии оказались бы «в будущем» и перестали быть видны.
```

Contrast (look-alikes):
```
Чем бит all-frozen карты видимости отличается от all-visible?
?
all-visible — все версии на странице видны всем снимкам; all-frozen — они ещё и заморожены.
↳ Страницы all-frozen может пропускать даже агрессивная очистка.
```

Observe:
```
Какой функцией `pageinspect` посмотреть заголовки версий строк на странице таблицы?
?
`heap_page_items(get_raw_page('имя_таблицы', номер_страницы))`
```

---

## 3. Part II — Buffer cache and WAL

```
Какой алгоритм вытеснения использует буферный кеш PostgreSQL?
?
Clock sweep: стрелка идёт по буферам по кругу, уменьшая счётчик использования; вытесняется буфер с нулём.

Почему большое последовательное сканирование не вытесняет из буферного кеша всё остальное?
?
Оно работает через небольшое буферное кольцо, повторно используя одни и те же буферы.
```

Why + knob:
```
Зачем при первом изменении страницы после контрольной точки в WAL пишется её полный образ?
?
Защита от частично записанной страницы: при восстановлении страница берётся из образа целиком.
↳ Управляет `full_page_writes`.
```

Scenario:
```
`checkpoint_timeout` уменьшили в 4 раза. Что происходит с объёмом WAL и почему?
?
Растёт: контрольные точки чаще, поэтому больше полных образов страниц после каждой из них.
```

Cloze for a canonical fact:
```
Контрольная точка сбрасывает на диск все ==грязные;;какие?== буферы, после чего журнал до её начала для восстановления не нужен.
```

---

## 4. Part III — Locks

Same fact, two angles (redundancy is fine when each angle is a different retrieval):
```
Где хранится информация о том, что строка заблокирована?
?
В заголовке самой версии строки на странице данных (поле `xmax` и информационные биты).

Почему блокировка миллиона строк не исчерпывает общую память под блокировки?
?
Блокировки строк хранятся на страницах данных, а не в таблице блокировок в общей памяти.
```

Enumeration handled per item (instead of "list all table lock modes"):
```
Какой режим табличной блокировки получает обычный `SELECT`?
?
`ACCESS SHARE`

Какой режим табличной блокировки получают `INSERT`, `UPDATE`, `DELETE`?
?
`ROW EXCLUSIVE`

Какой режим табличной блокировки конфликтует даже с `ACCESS SHARE`, то есть блокирует чтение?
?
`ACCESS EXCLUSIVE`
↳ Его берут, например, `DROP TABLE`, `TRUNCATE`, большинство вариантов `ALTER TABLE`.
```

---

## 5. Part IV — Query execution and statistics

```
Какая статистика столбца помогает планировщику выбрать между индексным и bitmap-сканированием?
?
`correlation` в `pg_stats` — насколько физический порядок строк совпадает с порядком значений.

Какое представление показывает собранную `ANALYZE` статистику по столбцам?
?
`pg_stats`
```

Code card (fenced block inside a `?` card — safe):
````
Узел плана показывает `Rows Removed by Filter: 99000` при `rows=1000`. Что это говорит о запросе?
```
Seq Scan on t (actual rows=1000 loops=1)
  Filter: (status = 'new')
  Rows Removed by Filter: 99000
```
?
Прочитано 100 000 строк ради 1 000: условие очень избирательно, вероятно, стоит индекс по `status`.
````

---

## 6. Part V — Index types

```
Почему BRIN почти бесполезен, если значения столбца случайно разбросаны по страницам?
?
BRIN хранит лишь сводку (например, min/max) для диапазона страниц; при плохой корреляции диапазоны перекрываются и читать приходится почти всё.

Зачем GIN-индексу список ожидающих вставок (pending list)?
?
Ускорить вставку: новые элементы копятся в списке и переносятся в основную структуру пачкой.
↳ Размер ограничивает `gin_pending_list_limit`; включается параметром `fastupdate`.
```

---

## 7. PostgreSQL 18 changes

Stamp the version in the question or answer; these are exactly the facts that become wrong when
the next edition comes out.
```
Составной индекс `(a, b)`, запрос `WHERE b = 42` без условия на `a`. Как PG 18 может использовать B-дерево?
?
Skip scan: для каждого различного значения `a` отдельный спуск по дереву за `b = 42`.
↳ Выгодно, когда различных `a` немного; появилось в PG 18.

PG 18: зачем добавили `autovacuum_vacuum_max_threshold`?
?
Ограничить сверху порог запуска автоочистки: на огромных таблицах доля `scale_factor` давала слишком большой порог.
```
