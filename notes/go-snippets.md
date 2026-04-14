# Go Snippets (friendly-snippets)

Доступны через blink.cmp в Neovim (`<Tab>` для применения).

## Импорты и пакеты

| Prefix | Результат |
|--------|-----------|
| `im` | `import "package"` |
| `ims` | `import (...)` блок |
| `pkgm` | `package main` + `func main()` |

## Переменные и типы

| Prefix | Результат |
|--------|-----------|
| `var` | `var name type` |
| `vars` | `var (...)` блок |
| `co` | `const name = value` |
| `cos` | `const (...)` блок |
| `tys` | `type Name struct {}` |
| `tyi` | `type Name interface {}` |
| `tyf` | `type Name func(...)` |
| `in` | `interface{}` |
| `map` | `map[type]type` |
| `ch` | `chan type` |
| `json` | `` `json:"field"` `` |
| `xml` | `` `xml:"field"` `` |

## Функции и методы

| Prefix | Результат |
|--------|-----------|
| `func` | Объявление функции |
| `fmain` | `func main()` |
| `finit` | `func init()` |
| `meth` / `fum` | Метод с receiver |
| `df` | `defer func(...)` |

## Управление потоком

| Prefix | Результат |
|--------|-----------|
| `if` | `if condition {}` |
| `ife` | `if ... else` |
| `el` | `else {}` |
| `ir` | `if err != nil { return nil, err }` |
| `for` | `for {}` |
| `fori` | `for i := 0; i < n; i++` |
| `forr` | `for _, v := range v {}` |
| `switch` | `switch expression {}` |
| `sel` | `select { case: }` |
| `cs` | `case condition:` |
| `om` | `if value, ok := map[key]; ok {}` |

## Горутины

| Prefix | Результат |
|--------|-----------|
| `go` | `go func() {}()` анонимная |
| `gf` | `go func(...)` |

## HTTP

| Prefix | Результат |
|--------|-----------|
| `wr` | `w http.ResponseWriter, r *http.Request` |
| `hf` | `http.HandleFunc(...)` |
| `hand` | HTTP handler функция |
| `rd` | `http.Redirect(...)` |
| `herr` | `http.Error(...)` |
| `las` | `http.ListenAndServe(...)` |
| `sv` | `http.Serve(...)` |
| `helloweb` | Hello world web app (полный шаблон) |

## Логирование и вывод

| Prefix | Результат |
|--------|-----------|
| `fp` | `fmt.Println("...")` |
| `ff` | `fmt.Printf("...", var)` |
| `lp` | `log.Println(...)` |
| `lf` | `log.Printf(...)` |
| `lv` | `log.Printf` с переменной (`%#+v`) |

## Тестирование

| Prefix | Результат |
|--------|-----------|
| `tf` | `func TestXxx(t *testing.T)` |
| `tm` | `func TestMain(m *testing.M)` |
| `bf` | `func BenchmarkXxx(b *testing.B)` |
| `ef` | `func ExampleXxx()` |
| `tdt` | Table-driven test (полный шаблон) |
| `tl` / `tlf` / `tlv` | `t.Log`, `t.Logf`, `t.Logf` с переменной |

## Прочее

| Prefix | Результат |
|--------|-----------|
| `make` | `make(type, 0)` |
| `new` | `new(type)` |
| `pn` | `panic("...")` |
| `sort` | Реализация `sort.Interface` |

---

Источник: [rafamadriz/friendly-snippets](https://github.com/rafamadriz/friendly-snippets/blob/main/snippets/go.json)
