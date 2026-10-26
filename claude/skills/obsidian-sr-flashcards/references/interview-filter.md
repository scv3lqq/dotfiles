# Interview filter: which facts deserve a card

The owner makes cards to prepare for backend interviews (senior level) and to avoid wrong
decisions at work. A card costs reviews for years; a fact that is one search away is not worth
that. Apply this filter BEFORE writing any card, including facts a skill tells you to add from
the book. Fewer, better cards: an empty set for a note is a valid result. Deciding WHAT to card
is harder than wording it, so this file is mostly about selection. The same file is the rulebook
of the `card-reviewer` agent: write so that it would pass.

## The main test
"An interviewer asks this and the candidate doesn't know. Is that a noticeable minus for a
senior backend engineer?" No → no card.

A card passes if at least one is true:
1. Backend interviews actually ask it, or it's needed to answer such a question.
2. Without it I make a wrong decision at work (wrong index, race, deadlock, goroutine leak,
   slow query, lost data, bloat).
3. It explains WHY the technology behaves this way (mechanism, not a name).

## Priorities
- **P1, always:** mechanisms one level below what the user sees; default behaviour that changes
  results; trade-offs and choosing between alternatives; common mistakes and gotchas; edge
  cases; complexity of operations; diagnosing typical problems (symptom → cause).
- **P2, senior:** deeper internals (data structures, algorithms, planner, storage) when they are a
  frequent interview topic.
- **P3, never, even if the source stresses it:** rare config and storage parameters; exact names
  of internal structures, fields, flags, system columns, catalog tables, views, functions;
  numeric constants and limits that don't drive decisions (header sizes, bit counts, byte
  offsets); directory layout (`PGDATA/...`); SQLSTATE codes and error texts (except ones code
  branches on, like `40001`); full signatures and all options of a command; psql/tool switches;
  version history and dates (except changes that change behaviour); narrow scenarios that come
  up once in several years (snapshot export, catalog snapshot); comparisons with a feature of
  another DBMS (flashback); anything trivially derived from a card that already exists; "what
  the book's author calls X".

Depth rule: know the MECHANISM, not the IDENTIFIERS. Exception: names that are the common
interview vocabulary (MVCC, WAL, HOT, xmin/xmax, VACUUM, TOAST, GMP, checkpointer).

## Internals sources (Rogov and the like)
Expect most of the chapter to land in P3. That is normal: take the mechanisms and their
practical consequences, not every detail in turn. A chapter's notes may be rich while its
cards are few; 0 cards for a note is fine. The book's worked examples are never cards (rule
"no exercises" below).

## Calibration
PostgreSQL
- ✅ Почему запрос может не использовать существующий индекс?
- ✅ Какую аномалию ещё допускает REPEATABLE READ в PostgreSQL?
- ✅ Как часто берётся снимок данных в READ COMMITTED?
- ✅ Почему долгая транзакция мешает VACUUM даже на таблицах, к которым она не обращалась?
- ✅ Чем сессия в состоянии idle in transaction опасна для VACUUM?
- ✅ Какие мёртвые версии строк VACUUM может удалить? (горизонт, tied to its consequence)
- ✅ Почему мгновенный ALTER TABLE может остановить все запросы к таблице?
- ✅ Почему ROLLBACK в PostgreSQL такой же дешёвый, как COMMIT?
- ❌ Изменения каких транзакций видны в снимке xmin:xmax:xip_list? (notation; ask the meaning:
  «только зафиксированных до создания снимка»)
- ❌ Почему версия с xmin = 810, xmax = 811 видна в снимке 809:811:809? (exercise on book numbers)
- ❌ Как курсор не видит свои новые строки? (command id, cmin/cmax: implementation identifiers)
- ❌ Чем отличается удержание горизонта настоящей и виртуальной транзакцией? (internal
  distinction; the practical point is idle in transaction)
- ❌ Как экспортировать снимок в другую транзакцию? (function names, narrow scenario)
- ❌ Почему в PostgreSQL невозможны flashback-запросы? (comparison with another DBMS)
- ❌ Какой storage-параметр переопределяет целевой размер строки для TOAST?
- ❌ Какой размер у заголовка страницы? В каком каталоге лежат файлы clog?
- ❌ В какой структуре разделяемой памяти хранится список активных транзакций? (ProcArray)
  ✅ instead: «По чему транзакция определяет, видна ли ей версия строки?»
- ❌ Зачем нужны hint bits? Зачем виртуальный номер транзакции? Почему SAVEPOINT сделан
  через подтранзакции? (internals for DBA / core developers, not backend)
- ❌ Ambiguous «Где проверяется / хранится X?»: user view (pg_stat_activity) vs internals both
  fit. Ask about the behaviour instead.

For every card from an internals book ask "is the answer a mechanism or just the name of a
structure?". A name → drop or turn it into the behaviour it explains.

Go
- ✅ Что произойдёт при записи в nil map?
- ✅ Что вернёт чтение из закрытого канала?
- ✅ Почему интерфейс, содержащий nil-указатель, не равен nil?
- ✅ Что происходит при append, если ёмкости слайса не хватает?
- ✅ Чем опасна горутина, которая ждёт канал, в который никто не напишет?
- ❌ Точная формула роста ёмкости слайса по диапазонам размеров
- ❌ Какое значение GODEBUG включает определённую трассировку?
- ❌ Перечисли имена всех полей структуры runtime.g

## Mix of card types
Facts alone train recitation; interviews need reasoning. Aim: about a third facts, two thirds
understanding.
1. Fact: «Какой уровень изоляции по умолчанию?»
2. Mechanism: «Что физически происходит со строкой при UPDATE с точки зрения MVCC?»
3. Contrast: «Главное отличие X от Y?» (one difference per card; always one for look-alikes:
   REPEATABLE READ/SERIALIZABLE, Mutex/RWMutex, WHERE/HAVING)
4. Scenario "что будет, если…": edge cases, errors, panics, locks
5. Choice / trade-off: «Когда выбрать X вместо Y?»
6. Diagnosis with a concrete condition: «Индекс по email есть, но `WHERE lower(email) = …` даёт
   Seq Scan. Почему?»
7. Code prediction: ≤10 lines, «Что выведет?» / «Где гонка?» / «Где утечка горутины?»
8. Cloze: only short closed ordered lists (≤5 items), one gap per card.

## Wording (checklist per card)
1. One thought per card: «и», «а также» or a list in the answer → split.
2. Start with a context label: `[PG]`, `[Go]`, `[Kafka]`, `[SQL]`.
3. Unambiguous: in six months, without the source, only one correct answer.
4. Ask it the way an interviewer would, with a precise question word: not «Как курсор не
   видит…», but «Почему…» / «За счёт чего…». No yes/no questions.
5. No hints: the question doesn't give the answer away; a long question with unusual words is
   remembered by its shape, not its meaning.
6. Answer: the gist in one sentence (≤15 words); extra explanation on a `↳` line, not graded.
7. No sets: «перечисли все…» is banned; a closed list → cloze; an open one → «назови два примера».
8. Mechanism tied to consequence: a mechanism card has its practical consequence in the same
   card or a neighbour (the transaction horizon matters because of what VACUUM can remove).
9. Several angles, no orphans: an important concept gets 2–3 cards (what, how, consequence); an
   isolated single card on a topic: add a related one or drop it.
10. No exercises on concrete values from the source (transaction numbers, addresses, numbers
    from the book's demo): card the rule, not the answer to the book's example.
11. Stamp version-dependent behaviour (`с PG 17`, `Go ≥ 1.22`).
12. Terms stay in English (MVCC, deadlock, goroutine), the rest in Russian.
13. Not sure a fact is right → don't card it as a fact; flag it in the report.

## Volume
Count = the number of interview-relevant atomic facts, never padded to a target. Typical:
0–3 cards per atomic note, 5–20 per dense book chapter (the low end for an internals
chapter: chapter 4 of Rogov, snapshots, is worth about 5). More than 40 for one topic means the
topic is too wide: split it.
