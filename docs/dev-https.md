# HTTPS для локального dev

Адреса: `https://dev.sellgar.ru/` и `https://admin.dev.sellgar.ru/`.
Выпуск и продление бесплатных сертификатов Let’s Encrypt выполняет уже
установленный cert-manager. TLS завершается на Traefik; приложения получают
ссылку на Secret `sellgar-dev-tls` через свой Helm-параметр `ingress.tlsSecretName`.
Покупка или ручная загрузка сертификатов не требуется.

Проверено 20 ноября 2026 года: три Deployment cert-manager доступны, Issuer
`sellgar-dev/letsencrypt` создан и имеет `Ready=True`. ACME-аккаунт зарегистрирован.
Secret `cert-manager/regru-api` создан владельцем через локальный терминал;
чтение зоны через API проверено из VM. Deployment `regru-webhook` и его APIService
Available. Certificate `sellgar-dev-tls` имеет `Ready=True`, издатель —
Let's Encrypt YR1, SAN содержит только два dev-имени. Срок действия до
18 февраля 2027 года; cert-manager запланировал продление на 19 января 2027 года.
После публикации делегирования DNS-проверка завершилась автоматически.
В локальный hosts добавлены оба dev-имени с адресом VM `192.168.122.10`.

Все шесть релизов раскатаны автоматически через CI → Helm OCI → Argo CD и имеют
`Synced/Healthy`. Ingress публикуют только dev-домены; обе страницы и ветки API
отвечают по HTTPS с обычной проверкой сертификата. HTTP возвращает 301 на HTTPS
с сохранением пути. Service worker админки зарегистрирован как `/sw.js` со scope
`https://admin.dev.sellgar.ru/`. В браузере проверены карточка товара, добавление
в корзину и удаление через степер с сокетным обновлением; исходное количество 0
восстановлено. Новых ошибок в console админки и витрины нет.

Проверенные Helm-релизы:

| Приложение | Версия dev-пакета |
|---|---|
| Admin UI | `0.44695816219.1` |
| Storefront | `0.44695826887.1` |
| Admin gateway | `0.44695836843.1` |
| Client gateway | `0.44695848163.1` |
| Socket gateway | `0.44695857162.1` |
| Media | `0.44695866457.1` |

## Проверка домена

VM находится в локальной сети. Для неё используется ACME DNS-01: Let’s Encrypt
проверяет публичную TXT-запись, а не доступность VM через интернет.
Изменение `/etc/hosts` направляет браузер на VM, но не подтверждает владение
доменом перед Let’s Encrypt.

DNS-проверку выполняет готовый webhook
[Flant cert-manager-webhook-regru](https://github.com/flant/cert-manager-webhook-regru).
cert-manager поддерживает внешние DNS-провайдеры через
[официальный webhook API](https://cert-manager.io/docs/configuration/acme/dns01/webhook/).
Собственный ACME-клиент или DNS-контроллер не разрабатывается.

## Ресурсы

- `bootstrap/operators/cert-manager/` — установленный cert-manager.
- `bootstrap/operators/regru/` — DNS webhook и его внутренний TLS.
- `bootstrap/traefik/` — штатный K3s HelmChartConfig с перенаправлением HTTP на HTTPS.
- `environments/dev/platform/letsencrypt-issuer.yaml` — ACME Issuer только для dev.
- `environments/dev/platform/website-certificate.yaml` — запрос сертификата на два dev-адреса.

Доступ REG.RU берётся из существующего Kubernetes Secret `cert-manager/regru-api`:
ключи `username` и `password`. Значения не входят в manifests, Helm values или Git.
Для API REG.RU требуется разрешённый исходящий IP. Настройка доступа в аккаунте
регистратора выполняется владельцем отдельно; установка cert-manager этих прав
не предоставляет.

Для новой среды владелец задаёт `regru_username` и `regru_password` в файле
Ansible Vault. Затем выполняет из `ansible/`:

```bash
ansible-playbook -i inventory/dev.yml dns.yml --ask-vault-pass -e @../.local/dev-vault.yml
```

Существующий Secret сохраняется; новые значения не передаются в аргументах
команды или логах. Подготовка: [Ansible](../ansible/README.md).

Webhook подготовлен из chart Flant, source commit
`f27a1e2817f0ba4d5dfde789fea2e82eb9391c2a`, образ 1.3.2 закреплён по digest.
Ссылка на существующий Secret заменяет генерацию Secret из Helm values.
Широкая upstream-роль чтения Secrets не включена: используемый код получает
credentials через environment, а Secret монтирует kubelet.
В pod явно указаны UID/GID 65532 штатного пользователя distroless `nonroot`.

## Порядок активации

1. Проверить публичное делегирование `sellgar.ru` на `ns1.reg.ru`, `ns2.reg.ru`.
2. Предоставить разрешённый владельцем доступ DNS API через Secret `regru-api`.
3. Установить webhook: `kubectl apply --server-side -k bootstrap/operators/regru`.
   Дождаться Available у Deployment `cert-manager/regru-webhook` и APIService
   `v1alpha1.acme.sellgar.ru`.
4. Применить Issuer и Certificate из файлов выше. Проверить `Ready=True` у
   Certificate `sellgar-dev/sellgar-dev-tls`. Готовность одного Issuer подтверждает
   регистрацию ACME-аккаунта, но не успешную DNS-проверку или выпуск сертификата.
5. Оба файла включены в `platform/kustomization.yaml`, а `Issuer` и `Certificate`
   группы `cert-manager.io` разрешены в `platform-project.yaml` для GitOps.
   Изменения опубликованы в инфраструктурный Git и приняты Argo CD;
   локальные файлы сами по себе сервер не обновляют.
6. Направить оба адреса на IP VM на локальном компьютере. Затем публиковать Helm
   конфигурацию приложений. После проверки сертификата и HTTPS-маршрутов применить
   `kubectl apply --server-side -k bootstrap/traefik` для HTTP → HTTPS redirect.
   Параметр `ports.web.http.redirections.entryPoint` сверен с установленным chart
   Traefik 41.6.1; исходный K3s HelmChart вручную не редактируется.

При задержке делегирования cert-manager сохраняет pending Order/Challenge и
повторяет DNS-проверку. Не подменять её вручную зоной `ru.`, отключением проверки
TLS или самоподписанным сертификатом для браузера. Текущие HTTP Ingress и работающие
адреса не заменяются частично настроенным HTTPS.

## Повторное развёртывание на VPS

Эта настройка использует стандартные Kubernetes/cert-manager ресурсы и не зависит
от путей kubeconfig или адреса локальной VM. В новом кластере устанавливаются
операторы из `bootstrap/operators/`, предоставляется свой Secret `regru-api`,
разрешается исходящий IP VPS в REG.RU, затем применяются ресурсы нужной среды.
Публичные DNS-записи будут указывать на VPS; локальная запись hosts не переносится.

Для production нужны отдельные environment manifests, доменные имена и доступы.
Секреты и содержимое PVC не переносятся через Git. Подготовка VPS/K3s и prod
bootstrap остаются отдельным этапом: эта настройка HTTPS не означает, что
автоматическая установка всей production-инфраструктуры уже завершена.

Текущий запрос сертификата и Ingress относятся только к `dev.sellgar.ru` и
`admin.dev.sellgar.ru`. Для `sellgar.ru` и `admin.sellgar.ru` ресурсы не создаются.

Официальное описание проверки:
[Let’s Encrypt DNS-01](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge).
