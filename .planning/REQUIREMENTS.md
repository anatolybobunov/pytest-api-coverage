# Requirements: pytest-api-coverage Multi-Spec

**Defined:** 2026-03-11
**Core Value:** Разработчики могут запустить один `pytest` и получить отдельные отчёты покрытия для каждого микросервиса, не меняя тестовый код.

## v1 Requirements

### Config

- [ ] **CFG-01**: Пользователь может задать несколько спек через YAML/JSON конфиг-файл с полями `name`, `path`, `urls` на каждую спеку
- [ ] **CFG-02**: Плагин автоматически обнаруживает `coverage-config.yaml` / `coverage-config.json` в корне проекта без явного указания
- [ ] **CFG-03**: Пользователь может указать конфиг-файл явно через флаг `--coverage-config=path`
- [ ] **CFG-04**: Пользователь может задать одну спеку через CLI-флаги `--coverage-spec-name`, `--coverage-spec-path`, `--coverage-spec-url` (для простых случаев)
- [ ] **CFG-05**: Плагин выдаёт понятную ошибку при попытке совместить `--swagger` с multi-spec флагами

### Orchestration

- [ ] **ORC-01**: Плагин создаёт отдельный `CoverageReporter` для каждой спеки, фильтруя запросы по URL этой спеки
- [ ] **ORC-02**: HTTP-запросы, не совпадающие ни с одним URL из конфига, игнорируются (не вызывают ошибок)
- [ ] **ORC-03**: Плагин генерирует отдельный набор файлов отчётов для каждой спеки

### Output

- [ ] **OUT-01**: Имена файлов отчётов содержат префикс из имени спеки: `{name}-coverage.json`, `{name}-coverage.html`, `{name}-coverage.csv`
- [ ] **OUT-02**: Terminal summary показывает одну строку на спеку: покрытие в процентах, количество запросов, имя файла
- [ ] **OUT-03**: Terminal summary показывает итоговую строку с суммарным покрытием и счётчиком проигнорированных запросов

### Compatibility

- [ ] **COMPAT-01**: Флаг `--swagger` продолжает работать без изменений; выходные файлы по-прежнему именуются `coverage.json`, `coverage.html`, `coverage.csv`
- [ ] **COMPAT-02**: Multi-spec режим корректно работает с pytest-xdist: воркеры собирают данные, мастер генерирует все отчёты
- [ ] **COMPAT-03**: `SpecConfig` сериализуется для передачи через xdist `workerinput` канал

### Settings

- [ ] **SET-01**: `is_enabled()` возвращает `True` при любом из трёх источников конфигурации: `--swagger`, `--coverage-spec-path`, или наличие конфиг-файла
- [ ] **SET-02**: `write_reports()` принимает опциональный параметр `prefix`; при `prefix=None` поведение идентично текущему

## v2 Requirements

### Config

- **CFG-V2-01**: Поддержка `pyproject.toml` как источника конфигурации (секция `[tool.pytest-api-coverage]`)
- **CFG-V2-02**: Поддержка переменных окружения для переопределения путей спек

### Output

- **OUT-V2-01**: Сводный HTML-отчёт по всем спекам с навигацией между ними
- **OUT-V2-02**: Машиночитаемый exit code в зависимости от порога покрытия (`--coverage-fail-under`)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Слияние отчётов нескольких спек в один | Каждая спека независима; смешение данных теряет ценность разделения |
| Динамическое переключение спек во время сеанса | Все спеки фиксируются на старте pytest |
| Форматы конфига кроме YAML и JSON | PyYAML уже есть в зависимостях; дополнительные форматы — излишество |
| Новые runtime-зависимости | Все нужные библиотеки уже присутствуют |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-01 | Phase 1: Config and Activation | Pending |
| CFG-02 | Phase 1: Config and Activation | Pending |
| CFG-03 | Phase 1: Config and Activation | Pending |
| CFG-04 | Phase 1: Config and Activation | Pending |
| CFG-05 | Phase 1: Config and Activation | Pending |
| SET-01 | Phase 1: Config and Activation | Pending |
| SET-02 | Phase 2: Orchestration and File Output | Pending |
| ORC-01 | Phase 2: Orchestration and File Output | Pending |
| ORC-02 | Phase 2: Orchestration and File Output | Pending |
| ORC-03 | Phase 2: Orchestration and File Output | Pending |
| OUT-01 | Phase 2: Orchestration and File Output | Pending |
| COMPAT-03 | Phase 2: Orchestration and File Output | Pending |
| OUT-02 | Phase 3: Terminal Summary and Compatibility | Pending |
| OUT-03 | Phase 3: Terminal Summary and Compatibility | Pending |
| COMPAT-01 | Phase 3: Terminal Summary and Compatibility | Pending |
| COMPAT-02 | Phase 3: Terminal Summary and Compatibility | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after roadmap creation*
