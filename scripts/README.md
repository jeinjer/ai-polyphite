# Scripts

Automatización local explícita y no destructiva.

- `bootstrap.ps1`: crea el entorno Python e instala dependencias locales.
- `start.ps1`: inicia Docker Desktop si es necesario, levanta todo el stack y
  espera hasta que API y dashboard estén listos.
- `check.ps1`: ejecuta audit, lint, typing, unit tests, build y validación de
  Compose sin modificar código fuente.

Inicio cotidiano del laboratorio:

```powershell
.\scripts\start.ps1
```

El comando reconstruye imágenes usando la caché de Docker. Para limitarse a
encender las imágenes existentes puede usarse `-SkipBuild`.

Para incluir las pruebas de integración contra PostgreSQL y Redis en ejecución:

```powershell
.\scripts\check.ps1 -Integration
```

Para incluir Playwright:

```powershell
$env:PLAYWRIGHT_BROWSER_CHANNEL = "chrome"
.\scripts\check.ps1 -E2E
```

Los flags se pueden combinar. `-Integration` requiere que PostgreSQL y Redis
estén accesibles mediante `DATABASE_URL` y `REDIS_URL`.

Los comandos equivalentes permanecen documentados en el README raíz para no
hacer que los scripts sean una dependencia oculta.
