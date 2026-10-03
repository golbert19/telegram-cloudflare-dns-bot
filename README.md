# Telegram Cloudflare DNS Bot
Bot de Telegram desarrollado en Python para la gestión automatizada y temporal de subdominios en Cloudflare. Permite crear registros tipo `A` apuntando a una VPS, delegar zonas mediante registros `NS` y administrar el acceso por tiempo limitado a través de una base de datos local SQLite.
---
## Características
- **Registros A automáticos:** Creación rápida de subdominios apuntando a la IP configurada de la VPS.
- **Delegación DNS (NS):** Configuración de múltiples servidores de nombres para subdominios delegados.
- **Control de acceso temporal:** Concesión de permisos a usuarios por número de días.
- **Gestión administrativa:** Consulta de usuarios activos y revocación inmediata de accesos.
- **Persistencia local:** Control de vigencia y autorizaciones mediante SQLite (`usuarios.db`).
- **Servicio 24/7:** Configuración lista para desplegarse como servicio en segundo plano con `systemd`.
---
## Configuración predeterminada

| Parámetro | Valor por defecto |
| :--- | :--- |
| **Dominio base** | `golbertvps.net.pe` |
| **IP VPS** | `45.41.207.172` |
| **Telegram Admin ID** | `8823167645` |
| **Ruta en VPS** | `/opt/telegram-cloudflare-dns-bot` |
| **Repositorio** | `https://github.com/golbert19/telegram-cloudflare-dns-bot` |

---
## Comandos del Bot
### Comandos de Usuario

| Comando | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `/start` | Mensaje de bienvenida e instrucciones | `/start` |
| `/miid` | Muestra el Telegram User ID del remitente | `/miid` |
| `/estado` | Verifica el estado del acceso y los días restantes | `/estado` |
| `/sub <nombre>` | Crea un registro `A` hacia la IP de la VPS | `/sub cliente01` |
| `/ns <subdominio> <ns1> <ns2>...` | Crea registros `NS` delegados para el subdominio | `/ns tunel ns1.midns.com ns2.midns.com` |

### Comandos de Administrador

| Comando | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `/dar <ID> <DIAS>` | Autoriza el acceso a un usuario por N días | `/dar 123456789 7` |
| `/quitar <ID>` | Revoca inmediatamente el acceso de un usuario | `/quitar 123456789` |
| `/usuarios` | Lista todos los usuarios con suscripción activa | `/usuarios` |

--
