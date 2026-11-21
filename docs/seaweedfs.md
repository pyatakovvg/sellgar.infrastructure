# SeaweedFS и CDN

Dev использует официальный Helm chart SeaweedFS 4.54.0 и образ 4.54,
закреплённый linux/amd64 digest. Источник chart:
https://seaweedfs.github.io/seaweedfs/helm

Конфигурация: `environments/dev/storage/seaweedfs/values.yaml`.
Argo Application `dev-seaweedfs` читает upstream chart и values из этого Git.
Ansible устанавливает bootstrap; реализацию StatefulSet/Deployment не копируем.

## Хранение и доступ

Один all-in-one pod, PVC `seaweedfs-all-in-one-data`, 10 GiB, local-path.
Для одного узла используется upstream `Recreate`: два процесса не пишут в
один локальный том. Масштабирование будущего хранилища требует отдельной
конфигурации компонентов; увеличение replicas all-in-one не является HA.

S3 Service: `seaweedfs-all-in-one:8333`, бакет `sellgar`.
S3 API, filer и master не имеют публичного Ingress. Публичный маршрут проходит
через Media: `https://cdn.dev.sellgar.ru/images/<fileUuid>`.
`cdn.sellgar.ru` зарезервирован для будущей prod-среды.

`seaweedfs-s3-config` содержит только `${ENV}` ссылки. Значения подставляет
SeaweedFS из Secret env refs: `media-storage` и исторического `minio-root`.
Media разрешены Read/Write/List/Tagging только своего бакета; административные
операции и анонимный S3-доступ закрыты. Bucket создаётся штатным hook chart.

Media сохраняет текущий S3 SDK и имена `MINIO_*` env. Это названия существующего
контракта конфигурации, а не зависимость от запущенного MinIO. Проверены
bucketExists, putObject/getObject/statObject/removeObject и Content-Type.
Переписывать SDK ради смены S3 endpoint не требуется.

Chart 4.54.0 генерирует неиспользуемый SFTP Secret даже при отключённом SFTP.
Его случайные данные исключены из Argo diff штатным `ignoreDifferences`;
SFTP listener не включён. Сам chart не патчится и не форкается.

## Перенос из MinIO, 21 ноября 2026

Перенос выполняется штатным `mc mirror --overwrite --preserve` через S3.
Ключи объектов, fileUuid и metadata File не меняются. До переключения проверены
все 36 объектов: 494480 bytes, одинаковые SHA-256 и Content-Type.
Сохранение данных проверяется после пересоздания SeaweedFS pod.

Порядок переключения:

1. Создать отдельный PVC и установить SeaweedFS.
2. Проверить доступ текущим SDK Media и скопировать объекты.
3. Повторно сверить объекты после последней записи в старое хранилище.
4. Опубликовать Helm values Media с endpoint SeaweedFS и CDN host.
5. Дождаться сертификата, healthy Media и проверить чтение через HTTPS.
6. После повторной сверки удалить StatefulSet/Service MinIO и PVC `data-minio-0`.
   Старый том не сохраняется: пользователь явно подтвердил удаление MinIO после
   сохранения изображений в SeaweedFS.

Если во время переключения кто-либо загружает или удаляет файлы, перед
финальной сверкой нужно кратко приостановить операции записи через Media.
Одновременную запись в два S3 backend не используем.

Слой раздачи пока представляет origin для CDN. Само отдельное доменное имя не
создаёт распределённый кеш: внешний CDN подключается к публичному Media endpoint.
Существующий Client gateway read proxy остаётся совместимым для старых URL.
Новые CDN URL админки задаются её собственным ConfigMap.

## Проверка

```bash
kubectl -n sellgar-dev get deployment seaweedfs-all-in-one
kubectl -n sellgar-dev get pvc seaweedfs-all-in-one-data
kubectl -n argocd get application dev-seaweedfs dev-media-service
kubectl -n sellgar-dev get certificate sellgar-dev-tls
curl -I https://cdn.dev.sellgar.ru/images/<existing-fileUuid>
```

Ожидается 200, корректный Content-Type и Cache-Control Media; `/internal/objects`
через CDN не публикуется. S3 credentials в URL публичного CDN отсутствуют.
