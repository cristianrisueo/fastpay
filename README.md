# FastPay

Prototipo de pagos para aprender microservicios: `auth` (registro, login y JWT) y `wallet` (saldos y transferencias),
cada uno con su propio PostgreSQL.

## Requisitos

- Docker con Docker Compose
- [uv](https://docs.astral.sh/uv/) 0.12.22 (instala Python 3.14.8 y las dependencias de cada servicio)
- make y openssl

## Puesta en marcha

1. Genera la clave privada de desarrollo de auth **antes** de `make app`. Si no existe, Docker crea un directorio
   con su nombre en lugar del fichero y auth no arranca:

   ```sh
   cd services/auth && mkdir -p keys && openssl genrsa -out keys/jwt-dev.pem 2048
   ```

2. Copia la configuración de desarrollo en cada servicio (la usan `make migrate` y `make run`):

   ```sh
   cp services/auth/.env.example services/auth/.env
   cp services/wallet/.env.example services/wallet/.env
   ```

3. Instala las dependencias de cada servicio con `uv sync`, dentro de `services/auth` y de `services/wallet`.

## Comandos principales

`make help` muestra todos. Los que dicen `s=...` funcionan con `s=auth` o con `s=wallet`.

| Comando                        | Qué hace                                                            |
| ------------------------------ | ------------------------------------------------------------------- |
| `make up`                      | Levanta las bases de datos (auth en 5432, wallet en 5433)           |
| `make migrate s=...`           | Aplica las migraciones del servicio                                 |
| `make run s=...`               | Arranca la API con recarga (auth en 8001, wallet en 8002)           |
| `make app`                     | Levanta todo en contenedores: bases de datos, migraciones y APIs    |
| `make psql s=...`              | Consola SQL de la base de datos del servicio                        |
| `make check` / `make test`     | Formato, linter y tipos / tests unitarios y de integración          |
| `make stop` / `make down`      | Apaga o elimina los contenedores (los datos se conservan)           |

## Crear una cuenta en wallet

Hasta que llegue Kafka, wallet no se entera de los registros de auth: la cuenta se crea a mano, con el `id` que
devuelve `POST /v1/register` de auth.

```sh
make psql s=wallet
```

```sql
INSERT INTO accounts (user_id, email, balance) VALUES ('<id de auth>', 'ana@example.com', 100);
```
