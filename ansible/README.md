# Ansible bootstrap

Ansible подготавливает узлы и подключает GitOps. Argo CD управляет работающей
платформой и приложениями; CI Product выполняет собственные migrate/deploy.
Бизнес-сиды и воспроизведение событий в bootstrap не запускаются.

Используются готовая коллекция [k3s-ansible](https://github.com/k3s-io/k3s-ansible)
и [kubernetes.core](https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/).
Собственных Python-модулей, shell-установщиков и обёрток нет.

## Установка инструментов

На управляющей машине нужен Python 3.12+, `venv`, Git и `kubectl` в PATH.
Из этого каталога:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/ansible-galaxy collection install -r requirements.yml
```

Все команды ниже выполняются из `ansible/`.
Коллекции устанавливаются в игнорируемый `.collections/`, Python-пакеты — в
`.venv/`; системный Python и глобальные Ansible collections не изменяются.

`inventory/dev.yml` описывает
существующую VM. Для VPS создаётся отдельный inventory с его IP, SSH-пользователем,
ключом, версией K3s и путём kubeconfig. Адреса prod сейчас не выдумываются.

## Новый сервер

```bash
.venv/bin/ansible-playbook -i inventory/dev.yml k3s.yml --syntax-check
.venv/bin/ansible-playbook -i inventory/dev.yml k3s.yml
```

Это настоящий установочный playbook upstream, а не проверка работающего узла.
Он может перезапускать K3s при повторном запуске. Не включать его в CI каждого
сервиса. Для текущей работающей VM установка заново не требуется.
Её MTU 1380 принадлежит локальной VPN-сети и описан в `bootstrap/local-vm/`;
не переносить эту настройку автоматически на VPS.

## Credentials и GitOps

`secrets.yml` создаёт отсутствующие пароли БД, S3 и ключи подписи штатным lookup
`ansible.builtin.password`. Существующие Secrets сохраняются, включая их значения.
Секретные задачи используют `no_log`; пароли в Git и логах отсутствуют.
Ротация паролей не является операцией bootstrap.

Для новой среды registry/DNS credentials предоставляет владелец. Создать
зашифрованный файл вне Git или в игнорируемом `.local/`:

```bash
mkdir -p ../.local
.venv/bin/ansible-vault create ../.local/dev-vault.yml
```

В редакторе задать `registry_username`, `registry_password`, `regru_username`,
`regru_password`. Значения не передавать в командной строке. GitHub token должен
иметь доступ к нужным GHCR packages. Для REG.RU используется API-пароль.
Пароль Vault хранится отдельно от файла; сам файл нужно резервировать безопасно.
Если соответствующие Secrets уже существуют, эти переменные не требуются.

```bash
.venv/bin/ansible-playbook -i inventory/dev.yml secrets.yml --check
.venv/bin/ansible-playbook -i inventory/dev.yml bootstrap.yml --ask-vault-pass -e @../.local/dev-vault.yml
```

Порядок `bootstrap.yml`: credentials → cert-manager → CNPG/RabbitMQ operators →
Argo CD → registry/DNS credentials → DNS webhook → root dev Application.
После подключения root Application GitOps устанавливает платформу, включая
SeaweedFS из официального Helm chart. Для проверки уже работающего кластера:

```bash
.venv/bin/ansible-playbook -i inventory/dev.yml bootstrap.yml --check
```

Первоначальный dry-run на совершенно пустом кластере не создаёт CRD/namespace,
поэтому не может проверить последующие custom resources. Проверка нового сервера
требует действительной установки в отдельный кластер.

`registry.yml` использует только явно созданный Kubernetes Secret `ghcr-pull`;
Docker config и аккаунты на управляющей машине не сканируются. `dns.yml`
можно запускать отдельно с Vault; существующий `cert-manager/regru-api` сохраняется.

Доступ к данным для разработчика остаётся через постоянные systemd-туннели из
`bootstrap/local-vm/`. Ansible bootstrap не останавливает watcher или туннели.

## Выполненные проверки

21 ноября 2026: syntax-check установочного playbook K3s и всего bootstrap;
полный bootstrap в check mode на существующем dev — без ошибок и force-conflicts.
Создание credentials проверено в отдельном временном namespace; повторный запуск
показал changed=0. Проверочный namespace удалён. Существующая VM не переустанавливалась;
развёртывание с нуля на отдельном VPS ещё не проверено.

## GitHub delivery runners

`runners.yml` подготавливает общий organization-level runner для dev.
Состав — `delivery_runners` в inventory: один на среду, максимум два всего.
Число приложений не влияет на размер pool. Пустая `delivery_organization`,
повтор среды или превышение лимита останавливают playbook до изменения узла.
Официальный archive закреплён SHA-256; пользователь runner не получает sudo/Docker.
Подготовка и регистрация разделены штатными Ansible tags `prepare`/`register`.
Первая не регистрирует исполнителей в GitHub; вторая требует short-lived organization token
через игнорируемый Vault file и использует upstream `config.sh`/`svc.sh`.

`delivery_runners[].kubeconfig_source` указывает внутри VM на namespace-scoped
credential; K3s administrator config сюда не подходит. На новом сервере сначала
нужно выпустить отдельный deployment credential и указать его путь в inventory.
Сначала создаётся согласованная организация и готовится перенос репозиториев:
[план перехода](../docs/organization-transition.md). Регистрация и включение delivery
выполняются до публикации workflow приложения,
чтобы migrate/deploy не остались в очереди. Детали и команды:
[доставка приложений](../docs/application-delivery.md).
