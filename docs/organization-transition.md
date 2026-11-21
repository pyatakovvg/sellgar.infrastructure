# Общий исполнитель доставки Sellgar

## Задача и состояние

Запрос владельца: общий runner для всех сервисов; максимум два во всей системе.
Рабочие ветки остаются `development`. Сборки, юнит-тесты и публикация
образов выполняются на GitHub-hosted runners; migrate/deploy — в приватном контуре.
Production и reverse миграций не входят в этот переход.

21 ноября 2026 владелец создал организацию `sellgar` и разрешил подготовить перенос.
Удалены 11 ошибочно подготовленных repository-scoped аккаунтов, их home и копии
kubeconfig. Перед удалением проверено отсутствие регистрации. Проверка после
удаления: остался только активный Product runner, все dev Deployments готовы.

13 репозиториев перенесены в организацию `sellgar`; названия, public visibility
и default branch master сохранены. Общий runner `sellgar-dev` зарегистрирован
и запущен. Группа Default допускает ровно 12 приложений, public access включён.
Тег `delivery-v0.6.0` опубликован на commit `1a73029`. Product успешно прошёл
полную доставку через общий runner: [run 44941272922, attempt 2](https://github.com/sellgar/sellgar.product.service/actions/runs/44941272922),
source `0c5021d`, Helm revision 7, готовый pod и HTTP health `ok`.
Старый Product runner снят с регистрации; его служба, Linux account и home удалены.
В VM остался ровно один общий runner. Все 12 приложений переданы от Argo к Helm без удаления workloads и данных.
Контракт delivery-v0.7.0 ставит unit перед build; требуется проверка новых CI каждого приложения.

## Решение

Один официальный runner `sellgar-dev` уровня организации обслуживает разрешённые
репозитории. Одна Linux-учётная запись `delivery-dev-runner`, одна systemd-служба,
namespace-scoped kubeconfig. Установка — Ansible `runners.yml`, upstream архив
с SHA-256, `config.sh` и `svc.sh`. Нет ARC, динамической перерегистрации и runner
на каждый сервис. Inventory содержит одну запись; playbook допускает максимум
две и запрещает повтор среды. Вторая регистрация понадобится только при отдельном
вводе production с собственным узлом и credential; сейчас она не создаётся.

Новые jobs требуют одновременно метки `sellgar-delivery` и `sellgar-dev`.
У старого Product runner нет `sellgar-delivery`, поэтому он не сможет выполнить
проверочный запуск вместо общего исполнителя. Источник доказательства — runner
name в реальных migrate/deploy jobs, а не только зелёный статус pipeline.

На переходе старый Product runner и новый общий могут временно существовать вместе
(два всего). После успешной доставки Product через общий runner старый снимается
с регистрации и удаляется. Остальные сервисы не требуют новых исполнителей.

Общий pool ограничен 12 репозиториями приложений из списка ниже; infrastructure
в этот список не входит. Репозитории публичные, public access включён.
На GitHub Free ограничение Selected workflows недоступно; владелец явно согласовал
All workflows внутри выбранных репозиториев. Администратор репозитория может
изменить workflow и направить другую job на runner — метки не являются границей
безопасности. Поэтому workflow-файлы доверяются только владельцам репозиториев.
Организация требует одобрения всех external contributor PR workflows.
Development/master защищаются правилами PR и запретом force push/удаления;
доверенный администратор сохраняет возможность прямого push. Наши migrate/deploy
допускают только development push и ручной master release, PR/build/test используют
GitHub-hosted runners. Это согласованная модель GitHub Free, а не ограничение
исполнителя двумя workflow-файлами.

## Состав переноса

Проверены публичные метаданные GitHub: все 13 репозиториев public, не архивированы,
default branch `master`. Видимость и названия сохраняются; рабочая ветка development.
Новый owner — `sellgar`, прежний — `pyatakovvg`.
В интерфейсе всех 13 репозиториев проверены Secrets: repository/environment
secrets отсутствуют. Их значения не читались; credentials из VM в GitHub не передаются.

- sellgar.infrastructure
- sellgar.product.service
- sellgar.identity.service
- sellgar.shop.service
- sellgar.store.service
- sellgar.cart.service
- sellgar.file.service
- sellgar.media.service
- sellgar.socket.gateway
- sellgar.admin.gateway
- sellgar.client.gateway
- sellgar.ui.admin
- sellgar.ui.desktop

Workspace, mobile и общие библиотеки не переносятся в этой операции. Их владельцы и рабочие ветки сохраняются. Framework test loader исправлен отдельно; его gitlink синхронизирован в Admin, Desktop и Mobile. В workspace после переноса обновляются
соответствующие `.gitmodules`, remotes и gitlinks; nested library URL сохраняются.

## Последовательность перехода

1. Подготовить и проверить общий workflow и все callers до переноса. Не публиковать
   ссылки на ещё не созданный тег. Согласовать окно без новых push/release; проверить
   отсутствие активных delivery jobs, пока меняется owner общей инфраструктуры.
2. Зарегистрировать один organization runner с namespace-доступом; проверить Online,
   ограничение группы 12 приложениями, public access, external PR approval и RBAC.
   На Free оставить согласованный All workflows; Selected workflows требует Enterprise.
3. Перенести 13 репозиториев штатным GitHub transfer, сохранив названия/видимость.
   Проверить Secrets/variables/environments по именам без чтения их значений,
   разрешения Actions и ветки. Права организации могут отличаться от personal account.
4. Обновить `uses:` и checkout shared chart на `sellgar/sellgar.infrastructure`.
   У Actions нет redirect для reusable workflows; Git redirect этого не заменяет.
   Опубликовать проверенный общий workflow и новый immutable tag, затем callers.
   Существующие version tags не перемещать и не переписывать.
5. Новые образы публикуются в `ghcr.io/sellgar/<repository>` через GITHUB_TOKEN.
   Helm image/migration repositories должны совпадать. GHCR packages не меняют
   owner при transfer; старые `ghcr.io/pyatakovvg/...` сохраняются для работающих
   Deployment, истории и Argo OCI до фактического перехода каждого приложения.
   Проверить публикацию нового пакета и pull из dev с существующим `ghcr-pull`.
6. Сначала проверить полный Product pipeline через общий runner: unit → build → publish →
   migrate → deploy. Проверить миграционные логи, завершение Job,
   Helm revision, ожидаемый digest и readiness. Затем удалить старый Product runner.
7. По одному передавать остальные приложения от Argo к Helm CI без удаления workloads,
   БД и Secrets. Общий runner уже готов; создание новых runners запрещено.
   Для каждого проверить тесты, migrate при наличии БД, deploy и реальный endpoint.
   Admin/Client gateway, Media и UI не имеют migrate; Socket имеет.
8. Обновить GitOps root/platform Git URL, remotes и workspace pointers. OCI-источники
   ещё не переведённых приложений не переключать на несуществующие пакеты организации.

## Проверки до публикации

- Ansible syntax-check прошёл. Проверка actual preflight без install tasks:
  один dev и пара dev/prod допустимы; пустая организация, три runner и повтор dev
  дают ошибку до изменения хоста.
- Actionlint прошёл для shared workflows и всех 12 приложений.
- Helm lint и dev render прошли для всех 12 приложений, migration render — для
  семи приложений с БД. Это проверка конфигурации, не выполнение unit tests/миграций.
- Полные сборки и юнит-тесты выполняются в GitHub. Для Product все пять jobs
  успешны, migrate/deploy выполнил именно sellgar-dev. Остальные ожидают проверки.
- Переход завершён только после успешного реального GitHub run каждого приложения,
  проверки digest/readiness и подтверждения одного общего Online runner.

## Источники решения

- [Опыт команды с 50 репозиториями и общим dev runner, Stack Overflow CI/CD](https://stackoverflow.com/questions/77358634/organization-runner-not-showing-in-new-repositories).
- [Опыт двух self-hosted runners, r/devops](https://www.reddit.com/r/devops/comments/1nryntt/whats_your_ci_setup_and_do_you_like_it/).
- [Scope runner: repository / organization](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners).
- [Ограничение доступа runner groups](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).
- [Перенос Git, Secrets и deploy keys](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository).
- [Actions не поддерживает redirects](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations).
- [GHCR packages сохраняют owner и теряют прежнюю связь с repo](https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages).

## Подготовка инструментов

Первый Product attempt остановлен на медленной загрузке kubectl; миграция тогда
не запускалась. В стандартный setup-kubectl cache помещён официальный v1.37.2
с проверенным SHA-256. Повтор failed jobs сохранил успешные build/publish/tests,
выполнил migrate и deploy. Ansible теперь подготавливает этот cache штатным get_url
с checksum. Управление .env через lineinfile сохраняет остальные upstream-переменные.
Первая загрузка миграционного образа из GHCR заняла 7m47s; Job завершилась успешно.
