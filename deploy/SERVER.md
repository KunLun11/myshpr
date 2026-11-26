# Деплой на VPS рядом с vollmira

Пошаговая инструкция для сервера **4 ГБ RAM / 2 vCPU**, где уже работает
`vollmira.ru`, а `my-proekt.ru` нужно поднять на том же хосте.

---

## 0. Итоговая схема

```
Интернет ──► :80/:443  Caddy (контейнер `edge`, /opt/edge)  ── TLS для обоих доменов
                 │
                 ├── my-proekt.ru ──────────► 127.0.0.1:3000  Next.js (compose)
                 │                                └─ BFF /api/backend/* → FastAPI
                 ├── vollmira.ru /api/ /admin/ ► 127.0.0.1:8000  gunicorn (systemd)
                 ├── vollmira.ru /static/   ──► /home/deploy/vollmira-backend/staticfiles
                 ├── vollmira.ru /media/    ──► /home/deploy/vollmira-backend/media
                 └── vollmira.ru /          ──► /var/www/vollmira (React SPA)
```

| Компонент | Где | Кто обновляет |
| --- | --- | --- |
| edge-Caddy, vhost обоих сайтов, сертификаты | `/opt/edge/` (отдельный compose-проект `edge`) | вручную (`deploy/edge/`) |
| my-school-project: Next.js, FastAPI, worker, Postgres, Redis | `/srv/my-school-project` | `git pull` + `compose up -d --build` |
| vollmira: Django/gunicorn | `/home/deploy/vollmira-backend` (systemd) | CI `backend-deploy.yml` |
| vollmira: React SPA | `/var/www/vollmira` | CI frontend-репозитория (rsync) |

Почему отдельный compose-проект для Caddy: иначе `docker compose down` школьного
стека уронил бы вход и для vollmira.

---

## 1. Проверки до начала

```bash
# домен уже должен резолвиться в этот сервер (A-записи вы указали)
dig +short my-proekt.ru www.my-proekt.ru vollmira.ru www.vollmira.ru

# ресурсы
free -h; df -h /; nproc
docker --version && docker compose version        # нужна Compose >= 2.24

# кто занял 80/443
sudo ss -ltnp '( sport = :80 or sport = :443 )'
```

### 1.1 Если Docker не установлен

Ставить **из apt**, а не через snap: snap-пакет `docker` работает в строгом
конфайнменте и не видит произвольные каталоги хоста — bind-mount'ы
`/home/deploy/vollmira-backend/{media,staticfiles}` для edge-Caddy и
`/var/www/vollmira` работать не будут.

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 docker-buildx
sudo systemctl enable --now docker

# чтобы не писать sudo перед каждой командой
sudo usermod -aG docker "$USER"
newgrp docker          # или перелогиниться по SSH

docker --version && docker compose version && docker info >/dev/null && echo "docker ok"
```

Ротация логов и перезапуск контейнеров при обновлении демона (полезно на 4 ГБ):

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true
}
EOF
sudo systemctl restart docker
```

Проверка, что установка не задела рабочий сайт:

```bash
curl -s -o /dev/null -w 'vollmira: %{http_code}\n' https://vollmira.ru/
ss -ltnp | grep -E ':(80|443) '      # всё ещё nginx
```

> Порты контейнеров публикуются только на `127.0.0.1` (см.
> `docker-compose.server.yml`), а edge-Caddy работает в `network_mode: host`,
> поэтому правила ufw для 80/443 продолжают действовать.

Если `www.my-proekt.ru` **не** резолвится — в `deploy/edge/Caddyfile` удалите
блок `www.my-proekt.ru` (иначе Caddy будет бесконечно повторять выпуск
сертификата для несуществующего имени). То же для `www.vollmira.ru`.

Если `dig +short` вообще ничего не печатает — A-записи не видны. Сверьте
с публичным IP сервера и спросите публичные резолверы:

```bash
curl -s https://ifconfig.me/ip; echo          # публичный IP этого сервера
dig +short A my-proekt.ru @1.1.1.1
dig +short A my-proekt.ru @8.8.8.8
getent ahosts my-proekt.ru | head -2
```

Совпадает IP — проблема только в кэше локального резолвера
(`sudo systemd-resolve --flush-caches`). Не совпадает или пусто — правьте
A-запись у регистратора и ждите TTL.

## 2. Swap (обязательно на 4 ГБ)

Сборка Next.js на 2 vCPU легко занимает 1,5–2 ГБ и без swap может убить
работающий vollmira OOM-killer'ом.

```bash
free -h | grep -i swap          # если swap уже есть — шаг пропустить
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
printf 'vm.swappiness=10\n' | sudo tee /etc/sysctl.d/99-swap.conf
sudo sysctl --system
```

## 3. Код на сервере

Репозиторий приватный (`git@github.com:KunLun11/myshpr.git`) — добавьте
SSH-ключ сервера в GitHub → Settings → Deploy keys (read-only), либо клонируйте
по HTTPS с токеном.

```bash
sudo mkdir -p /srv/my-school-project
sudo chown -R "$USER":"$USER" /srv/my-school-project
git clone git@github.com:KunLun11/myshpr.git /srv/my-school-project
cd /srv/my-school-project
```

## 4. `deploy/.env`

```bash
cd /srv/my-school-project
python3 - <<'PY'
import pathlib, secrets
src = pathlib.Path("deploy/.env.example").read_text()
pg, rd, jwt = secrets.token_hex(24), secrets.token_hex(24), secrets.token_hex(32)
src = (src.replace("project.school.example", "my-proekt.ru")
          .replace("admin@school.example", "admin@my-proekt.ru")
          .replace("CHANGE-ME-STRONG-DB-PASSWORD", pg)
          .replace("CHANGE-ME-STRONG-REDIS-PASSWORD", rd)
          .replace("CHANGE-ME-AT-LEAST-32-CHARACTERS-LONG", jwt))
p = pathlib.Path("deploy/.env")
p.write_text("# Сгенерировано на сервере. Не коммитить, не публиковать.\n" + src)
p.chmod(0o600)
print("deploy/.env готов")
PY

grep -E '^(DOMAIN|ACME_EMAIL|POSTGRES_USER|CORS_ORIGINS|CSRF_TRUSTED_ORIGINS)=' deploy/.env
```

Проверьте руками:

- `DOMAIN=my-proekt.ru`, `ACME_EMAIL` — ваш реальный адрес;
- `CORS_ORIGINS` и `CSRF_TRUSTED_ORIGINS` = `https://my-proekt.ru` (без `/` в конце);
- `DATABASE_URL` и `REDIS_URL` содержат **те же** пароли, что `POSTGRES_PASSWORD`
  и `REDIS_PASSWORD` (скрипт выше это уже обеспечил);
- `BACKUP_DIR=/var/backups/my-school-project` — каталог вне диска приложения.

```bash
sudo mkdir -p /var/backups/my-school-project
sudo chown "$USER" /var/backups/my-school-project
```

## 5. Поднять стек (пока без публичного входа)

```bash
cd /srv/my-school-project
export COMPOSE_FILE=deploy/docker-compose.prod.yml:deploy/docker-compose.server.yml

docker compose config >/dev/null          # проверка синтаксиса
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=50 backend
```

`docker-compose.server.yml` — override для этого сервера: Caddy в стеке
отключён (порт 80/443 занят), а `frontend` опубликован только на loopback.

Проверка, что приложение живо без TLS:

```bash
curl -fsS -o /dev/null -w 'login: %{http_code}\n' http://127.0.0.1:3000/login
curl -fsS -o /dev/null -w 'readyz: %{http_code}\n' http://127.0.0.1:3000/api/backend/readyz
docker stats --no-stream            # ожидаемо ~0,8–1,2 ГБ суммарно
```

Если сборка упала по памяти (`Killed`, `exit 137`) — проверьте `free -h`,
убедитесь, что swap включён, и собирайте по сервисам:
`docker compose build backend && docker compose build frontend`.

## 6. Готовим edge и проверяем бэкенд vollmira

```bash
sudo mkdir -p /opt/edge
sudo cp /srv/my-school-project/deploy/edge/Caddyfile \
        /srv/my-school-project/deploy/edge/docker-compose.yml /opt/edge/
echo 'ACME_EMAIL=admin@my-proekt.ru' | sudo tee /opt/edge/.env
sudo chmod 600 /opt/edge/.env

# синтаксис Caddyfile до переключения
cd /opt/edge && sudo docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile" \
  caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

**Критичный префлайт** — gunicorn должен уже слушать TCP. Это делает обновлённый
systemd-юнит из репозитория (`--bind 127.0.0.1:8000`); он приезжает
автоматически при следующем деплое vollmira, а вручную ставится так:

```bash
cd /home/deploy/vollmira-backend && git pull
sudo cp deploy/systemd/vollmira.service /etc/systemd/system/vollmira.service
sudo systemctl daemon-reload && sudo systemctl restart vollmira
sleep 3
curl -s -o /dev/null -w 'vollmira напрямую: %{http_code}\n' \
  -H 'Host: vollmira.ru' http://127.0.0.1:8000/api/v1/
```

`200` или `401` — норма (API отвечает). `000`/`Connection refused` — дальше
переключаться нельзя, сначала почините юнит.

> Юнит сейчас слушает **и** `127.0.0.1:8000`, **и** старый unix-сокет. Это
> специально: переключение проходит без простоя, а после него строку
> `--bind unix:/run/vollmira/gunicorn.sock` и `RuntimeDirectory*` можно удалить.

## 7. Переключение входа (простой ~1–2 минуты)

Делайте, когда готовы: ровно в этот момент nginx останавливается, а Caddy
выпускает сертификаты.

```bash
# 1. освобождаем 80/443 и отключаем автопродление certbot
sudo systemctl stop nginx
sudo systemctl disable nginx
sudo systemctl disable --now certbot.timer

# 2. поднимаем единый вход
cd /opt/edge
sudo docker compose up -d
sudo docker compose logs -f caddy        # ждём "certificate obtained successfully"
```

Если сертификат не выпускается:

- `dig +short my-proekt.ru` → не IP сервера (DNS ещё не разошёлся);
- порт 80 закрыт файрволом: `sudo ufw status` / `sudo iptables -S`;
- имя из Caddyfile не резолвится (уберите `www.…`).

Для отладки без расхода лимитов Let's Encrypt раскомментируйте в Caddyfile
`acme_ca https://acme-staging-v02...` — но тогда браузер будет ругаться на
сертификат; после проверки верните боевой ACME и удалите том `edge_caddy_data`
(`cd /opt/edge && sudo docker compose down && sudo docker volume rm edge_caddy_data`).

## 8. Проверка

```bash
curl -I https://my-proekt.ru
curl -I https://vollmira.ru
curl -s -o /dev/null -w '%{http_code}\n' https://vollmira.ru/api/v1/

cd /srv/my-school-project
BASE_URL=https://my-proekt.ru deploy/scripts/smoke.sh
```

В браузере: вход в my-proekt.ru, загрузка файла (лимит 25 МиБ), вход в
`https://vollmira.ru/admin/`, фото профиля.

## 9. Эксплуатация

**Обновление приложения:**

```bash
cd /srv/my-school-project
git pull
export COMPOSE_FILE=deploy/docker-compose.prod.yml:deploy/docker-compose.server.yml
docker compose up -d --build
docker image prune -f
```

**Бэкапы (cron, ежедневно):**

```bash
crontab -e
# 0 3 * * * cd /srv/my-school-project && COMPOSE_FILE=deploy/docker-compose.prod.yml:deploy/docker-compose.server.yml deploy/scripts/backup.sh >> /var/log/myschool-backup.log 2>&1
```

**Правила, чтобы не сломать себя:**

- `docker compose down -v` в `/opt/edge` **удаляет сертификаты** (том
  `edge_caddy_data`) — не делайте этого; для перезапуска хватит `restart`.
- Тома `pg_data`, `media_data`, `redis_data` живут в compose-проекте
  `deploy`; удаление = потеря данных.
- Caddyfile правится в репозитории (`deploy/edge/Caddyfile`), затем копируется
  в `/opt/edge/` и применяется `sudo docker compose restart caddy`.
- Диск: `docker system prune -af --volumes` только осознанно (удалит и
  неиспользуемые тома).

**Откат на nginx (если что-то пошло не так):**

```bash
cd /opt/edge && sudo docker compose down
sudo systemctl enable --now nginx          # конфиг 443 на месте, сертификаты в /etc/letsencrypt
sudo systemctl enable --now certbot.timer
cd /home/deploy/vollmira-backend && git checkout <коммит-до-переезда> --
sudo cp deploy/systemd/vollmira.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl restart vollmira
```

## 10. Что закоммитить из этого набора

- `deploy/edge/Caddyfile`, `deploy/edge/docker-compose.yml` — общий вход обоих сайтов;
- `deploy/docker-compose.server.yml` — override для сервера с vollmira;
- `deploy/SERVER.md` — эта инструкция;
- в репозитории **vollmira-backend**: `deploy/systemd/vollmira.service`
  (`--bind 127.0.0.1:8000`) и `.github/workflows/backend-deploy.yml`
  (шаг nginx/certbot убран). Пока workflow не обновлён, очередной деплой
  vollmira упадёт на `systemctl reload nginx`.
