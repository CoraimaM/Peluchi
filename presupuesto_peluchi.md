# Presupuesto a 12 meses: API Peluchi

Fecha de elaboración: 19/11/2026
Moneda: dólares (USD), sin IVA.

## 1. Qué vamos a presupuestar

Peluchi es una API propia. Como todavía no tengo cifras de uso reales, he partido de un escenario razonable que se puede ajustar más adelante:

| Concepto | Supuesto |
|---|---|
| Servidor de la API | 1 vCPU y unos 2 GB de RAM, siempre encendido |
| Base de datos | PostgreSQL gestionada, 1-2 GB de RAM y 20 GB de almacenamiento |
| Tráfico | Unos 20 GB de salida al mes |
| Despliegue | Una sola región, sin alta disponibilidad, sin capas gratuitas |
| Periodo | 12 meses |

Proveedores comparados: Render, Azure, AWS y Google Cloud.

## 2. Resumen

| Proveedor | Configuración | Mes aprox. | 12 meses | 12 meses + 15 % de colchón |
|---|---|---|---|---|
| **Azure** | App Service B1 + PostgreSQL Flexible B1ms | ~$29 | ~$346 | ~$398 |
| **AWS** | EC2 t4g.small + RDS db.t4g.small | ~$43 | ~$518 | ~$596 |
| **Google Cloud** | Compute Engine e2-small + Cloud SQL db-g1-small | ~$47 | ~$562 | ~$646 |
| **Render (Hobby)** | Web service 1c-2g + Postgres 0.5c-1g | ~$52 | ~$627 | ~$721 |
| **Render (Pro)** | Lo mismo + workspace Pro | ~$75 | ~$900 | ~$1.035 |

En este escenario, Azure sale como la opción más barata y Render Pro como la más cara. Render compensa con un despliegue mucho más simple (conectas el repo y listo), algo que no se ve en el precio.

## 3. Desglose por proveedor

### Render

| Concepto | Mes |
|---|---|
| Web service 1 CPU / 2 GB | $25,00 |
| Postgres 0,5 CPU / 1 GB | $19,00 |
| Almacenamiento 20 GB × $0,30 | $6,00 |
| Salida de datos (5 GB incluidos en Hobby, resto a $0,15/GB) | $2,25 |
| **Total Hobby** | **$52,25** |
| Workspace Pro (incluye 25 GB de tráfico, así que no hay extra) | +$25,00 sobre compute y disco |
| **Total Pro** | **$75,00** |

Nota: el plan Hobby está pensado para proyectos personales y prototipos. Si Peluchi va a producción de verdad, lo razonable es contar con el Pro.

### Azure

| Concepto | Mes |
|---|---|
| App Service Linux Basic B1 (1 core, 1,75 GB) | $13,14 |
| Azure Database for PostgreSQL Flexible B1ms (1 vCPU, 2 GB) | ~$12,00 |
| Almacenamiento de la BD (mínimo 32 GB) | ~$3,70 (estimación) |
| Salida de datos (primeros 100 GB gratis) | $0,00 |
| **Total** | **~$28,84** |

### AWS

| Concepto | Mes |
|---|---|
| EC2 t4g.small | ~$12,26 (estimación) |
| Disco EBS gp3 20 GB | ~$1,60 (estimación) |
| RDS PostgreSQL db.t4g.small, una sola AZ | $23,36 |
| Almacenamiento RDS 20 GB gp3 | ~$2,30 |
| IPv4 pública | ~$3,65 (estimación) |
| Salida de datos (20 GB, dentro de lo gratuito) | $0,00 |
| **Total** | **~$43,17** |

### Google Cloud

| Concepto | Mes |
|---|---|
| Compute Engine e2-small | ~$13,00 |
| Disco de la VM 20 GB | ~$2,00 (estimación) |
| Cloud SQL PostgreSQL db-g1-small (1,7 GB) | ~$26,00 |
| Almacenamiento SSD de la BD 20 GB × $0,17 | ~$3,40 |
| Salida a internet 20 GB × $0,12 | ~$2,40 |
| **Total** | **~$46,80** |

## 4. Cosas a tener en cuenta

- **Los precios cambian.** Dependen de la región y se actualizan con frecuencia. Antes de dar cifras cerradas, conviene confirmarlas en las calculadoras oficiales de cada nube.
- **Las partidas marcadas como estimación** (EC2, discos, IPv4 de AWS y almacenamiento de Azure) las he calculado a partir de tarifas habituales y no las he verificado en las páginas oficiales.
- **Opciones más baratas, pero justas.** Cloud SQL db-f1-micro (~$8-9/mes) y RDS db.t4g.micro (~$12/mes) bajarían el coste, aunque con muy poca RAM (0,6 GB y 1 GB). Además, las instancias compartidas de Cloud SQL no entran en el SLA.
- **No incluido:** dominio, backups adicionales, monitorización, balanceador, ni alta disponibilidad. Poner la base de datos en Multi-AZ o HA prácticamente duplica ese componente.
- **Colchón del 15 %** para imprevistos (picos de tráfico, subir un escalón de instancia, etc.).

## 5. Fuentes

- Render: https://render.com/pricing
- Azure: https://azure.microsoft.com/pricing/details/app-service/linux/ y https://azure.microsoft.com/es-es/pricing/
- AWS: https://aws.amazon.com/rds/postgresql/pricing y https://aws.amazon.com/es/pricing/
- Google Cloud: https://cloud.google.com/sql/docs/postgres/pricing y https://cloud.google.com/pricing
- Comparativas de apoyo para instancias: bytebase.com/dbcost
